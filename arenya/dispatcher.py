"""The dispatcher: a deterministic loop that pulls jobs off the persisted queue and runs each one
as a Claude Agent SDK turn. No model decides who speaks next; the expectation rules in
engine.py do."""
from __future__ import annotations

import asyncio
import os
import time
import traceback

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, HookMatcher, RateLimitEvent,
                              ResultMessage, TextBlock, ToolUseBlock, query)

from . import acl, engine, prompts, state
from .config import ROOT, gear, role_of, roster, settings
from .tools import TurnContext, build_server

BUILTIN_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep"]
# Every tool schema is resent on every model call, so each job gets only what it uses.
PLAYER_TURN_TOOLS = ["Read"]
REFLECT_TOOLS = ["Read", "Write", "Edit"]


def tools_for(role: str, job: str) -> list[str]:
    if job == "reflect":
        return REFLECT_TOOLS
    if role in ("player", "npc"):
        return PLAYER_TURN_TOOLS
    return BUILTIN_TOOLS


class RateLimited(Exception):
    pass


class Dispatcher:
    def __init__(self, once: bool = False, verbose: bool = True):
        self.once = once          # exit when the queue drains instead of idling
        self.verbose = verbose
        self.tasks: dict[asyncio.Task, dict] = {}

    def say(self, text: str) -> None:
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)

    # ------------------------------------------------------------------ main loop
    async def run(self) -> None:
        if settings().get("auth") == "subscription":
            os.environ.pop("ANTHROPIC_API_KEY", None)
        with state.locked() as st:   # recover jobs orphaned by a crash
            st["queue"] = st["running"] + st["queue"]
            st["running"] = []
        self.say("dispatcher up")
        while True:
            st = state.load()
            if st["paused"]:
                if not self.tasks:
                    self.say(f"paused: {st['pause_reason'] or 'by human'} (uv run arenya resume)")
                    if self.once:
                        return
                    await self._wait_resume()
                    continue
            else:
                self._launch()
            if not self.tasks:
                if not self._idle() and self.once and not state.load()["queue"]:
                    return
                await asyncio.sleep(1)
                continue
            done, _ = await asyncio.wait(self.tasks, timeout=3, return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                job = self.tasks.pop(t)
                if t.exception():
                    self.say(f"!! {job['agent']}/{job['job']} crashed: {t.exception()!r}")

    async def _wait_resume(self) -> None:
        while state.load()["paused"]:
            await asyncio.sleep(3)

    def _launch(self) -> None:
        busy = {j["agent"] for j in self.tasks.values()}
        limit = settings()["concurrency"]
        with state.locked() as st:
            now = time.time()
            ready = sorted((j for j in st["queue"] if j.get("not_before", 0) <= now),
                           key=lambda j: (j["priority"], j["seq"]))
            for job in ready:
                if len(self.tasks) >= limit:
                    break
                if job["agent"] in busy:
                    continue
                st["queue"].remove(job)
                st["running"].append(job)
                busy.add(job["agent"])
                self.tasks[asyncio.create_task(self._run_job(job))] = job

    def _idle(self) -> bool:
        """Nothing queued or running. Wake the DM unless we're waiting on the human. Returns True if it queued work."""
        with state.locked() as st:
            if st["queue"] or st["running"]:
                return bool(st["queue"])
            if st["phase"] == "setup":
                return False
            owed = {a for e in st["expectations"] for a in e["waiting_on"]} - {"human"}
            if owed:
                # Self-heal: someone owes a response but has no job (e.g. benched mid-scene).
                agents = roster()
                for a in owed:
                    if agents.get(a, {}).get("status", "active") == "active":
                        engine.enqueue(st, a, "turn")
                    else:
                        engine._resolve(st, a, None, pass_all=True)
                return bool(st["queue"])
            if st["human_waiting"]:
                return False
            st["idle_wakes"] += 1
            if st["idle_wakes"] > settings()["idle_wakes_before_pause"]:
                st["paused"] = True
                st["pause_reason"] = "the DM keeps waking on an idle table without posting"
                reason = st["pause_reason"]
            else:
                engine.enqueue(st, "dm", "turn")
                return True
        engine.notify_human(f"game paused: {reason}")
        return False

    # ------------------------------------------------------------------ one job
    async def _run_job(self, job: dict) -> None:
        agent, kind, args = job["agent"], job["job"], job["args"]
        try:
            role = role_of(agent)
        except KeyError:
            self._finish(job)
            return
        ctx = TurnContext(agent=agent, role=role, job=kind)

        with state.locked() as st:
            g, why = engine.pick_gear(st, agent, kind)
            if "gear_cap" in job:
                g, why = min(g, job["gear_cap"]), why + f" (capped at {job['gear_cap']} after rate limits)"
            gr = gear(g)
            charges = engine.charges_left(st, agent)
            key = prompts.session_key(st, kind, args)
            sess = st["sessions"].get(agent)
            resume = sess["session_id"] if key and sess and sess.get("key") == key else None
            if kind in ("nudge", "replay") and not resume:
                kind = "turn"
            packet, cursor = prompts.wake_packet(st, agent, role, kind, args, gr, why, charges, resume is None)
            skip = (kind == "turn" and cursor == st["cursors"].get(agent, 0)
                    and not any(agent in e["waiting_on"] for e in st["expectations"])
                    and not (role == "dm" and st["idle_wakes"] > 0))
            if not skip:
                st["cursors"][agent] = cursor
        if skip:
            self._finish(job)
            return

        self.say(f"▶ {agent} {kind} · gear {gr['n']} {gr['model']}/{gr['effort']} ({why})")
        opts = ClaudeAgentOptions(
            system_prompt=prompts.system_prompt(agent, role),
            model=gr["model"],
            effort=gr["effort"],
            tools=tools_for(role, kind),
            allowed_tools=tools_for(role, kind) + ["mcp__arenya"],
            mcp_servers={"arenya": build_server(ctx)},
            # Without these, Claude Code attaches the account's claude.ai connectors (Notion,
            # Drive, …): ~95K tokens of tool schemas on every call. See docs/ARCHITECTURE.md § Cost.
            strict_mcp_config=True,
            env={"ENABLE_CLAUDEAI_MCP_SERVERS": "false"},
            hooks={"PreToolUse": [HookMatcher(matcher=acl.FILE_TOOLS, hooks=[acl.make_hook(agent, role)])]},
            setting_sources=[],
            cwd=str(ROOT),
            resume=resume,
            max_turns=settings()["roles"][role]["max_turns"],
        )
        result: ResultMessage | None = None
        started = time.time()
        try:
            async for msg in query(prompt=packet, options=opts):
                if isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, ToolUseBlock):
                            self.say(f"  {agent} · {b.name.removeprefix('mcp__arenya__')} {_brief(b.input)}")
                        elif isinstance(b, TextBlock) and b.text.strip() and self.verbose:
                            self.say(f"  {agent} ⋯ {b.text.strip()[:160]}")
                elif isinstance(msg, RateLimitEvent) and msg.rate_limit_info.status == "rejected":
                    raise RateLimited(msg.rate_limit_info)
                elif isinstance(msg, ResultMessage):
                    result = msg
            if result and result.is_error and (result.api_error_status == 429
                                               or "rate" in " ".join(result.errors or []).lower()):
                raise RateLimited(result.errors)
        except RateLimited as e:
            self._retry(job, gr["n"], f"rate limited: {e}")
            return
        except Exception as e:  # noqa: BLE001 — a bad turn must never kill the game
            engine.log("errors", {"agent": agent, "job": kind, "error": repr(e), "tb": traceback.format_exc()})
            self._retry(job, gr["n"], repr(e), downshift=False)
            return

        usage = result.usage if result else None
        engine.log("usage", {"agent": agent, "job": kind, "gear": gr["n"], "model": gr["model"],
                             "effort": gr["effort"], "why": why, "secs": round(time.time() - started, 1),
                             "turns": result.num_turns if result else None,
                             # SDK total_cost_usd is cumulative over a resumed session; estimate per turn instead.
                             "cost_usd": estimate_cost(gr["model"], usage),
                             "scene": prompts.session_key(state.load(), "turn", {}),
                             "usage": result.usage if result else None, "posted": ctx.posted,
                             "error": result.errors if result and result.is_error else None})
        with state.locked() as st:
            if result and key:
                st["sessions"][agent] = {"key": key, "session_id": result.session_id}
        self._after(job, ctx)

    def _after(self, job: dict, ctx: TurnContext) -> None:
        agent = job["agent"]
        if ctx.upshift_requested:
            self._finish(job, then=("replay", {}))
            return
        owed = engine.waiting_on(agent)
        if job["job"] in ("turn", "replay", "nudge") and owed and not ctx.passed:
            if job["job"] == "nudge":
                engine.pass_turn(agent, "(no response)")
                self._finish(job)
            else:
                self._finish(job, then=("nudge", {}))
            return
        self._finish(job)

    def _finish(self, job: dict, then: tuple[str, dict] | None = None) -> None:
        with state.locked() as st:
            st["running"] = [j for j in st["running"] if j["seq"] != job["seq"]]
            if then:
                engine.enqueue(st, job["agent"], then[0], then[1], priority=-1)

    def _retry(self, job: dict, gear_n: int, why: str, downshift: bool = True) -> None:
        backoff = settings()["rate_limit_backoff_s"]
        attempt = job["attempt"] + 1
        self.say(f"!! {job['agent']}/{job['job']} attempt {attempt}: {why}")
        with state.locked() as st:
            st["running"] = [j for j in st["running"] if j["seq"] != job["seq"]]
            if attempt > len(backoff):
                st["paused"] = True
                st["pause_reason"] = f"{job['agent']}/{job['job']} failed {attempt} times: {why[:200]}"
                st["queue"].insert(0, {**job, "attempt": 0})
            else:
                retry = {**job, "attempt": attempt, "not_before": time.time() + backoff[attempt - 1]}
                if downshift and attempt >= 2:
                    retry["gear_cap"] = max(1, gear_n - 1)
                st["queue"].append(retry)
            paused = st["paused"]
        if paused:
            engine.notify_human(f"game paused after repeated failures: {why[:200]}")


def estimate_cost(model: str, usage: dict | None) -> float | None:
    p = settings().get("prices", {}).get(model)
    if not usage or not p:
        return None
    return round((usage.get("input_tokens", 0) * p["input"] + usage.get("output_tokens", 0) * p["output"]
                  + usage.get("cache_read_input_tokens", 0) * p["cache_read"]
                  + usage.get("cache_creation_input_tokens", 0) * p["cache_write"]) / 1e6, 5)


def _brief(inp: dict) -> str:
    if "channel" in inp and "body" in inp:
        return f"[{inp['channel']}/{inp.get('type')}] {inp['body'][:100]!r}"
    s = ", ".join(f"{k}={str(v)[:60]}" for k, v in inp.items())
    return s[:160]
