"""In-process MCP tools ("mcp__arenya__*"). One server is built per agent turn so the sender
identity is bound by closure and can't be spoofed."""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field

import yaml
from claude_agent_sdk import create_sdk_mcp_server, tool

from . import channels, dice, engine, state
from .config import ROLES, ROOT, active, roster, save_roster


@dataclass
class TurnContext:
    agent: str
    role: str
    job: str
    posted: list[int] = field(default_factory=list)
    passed: bool = False
    upshift_requested: bool = False


def ok(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def err(text: str) -> dict:
    return {"content": [{"type": "text", "text": f"ERROR: {text}"}], "is_error": True}


def _list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    return list(v)


STR_LIST = {"type": "array", "items": {"type": "string"}}


def build_server(ctx: TurnContext):
    agent, role = ctx.agent, ctx.role
    tools = []

    # ------------------------------------------------------------------ everyone
    @tool("post", "Post a message to a channel. This is the ONLY way to speak. See rules/messaging.md.", {
        "type": "object",
        "properties": {
            "channel": {"type": "string", "description": "table | ooc | whisper-<pc> | backstage | human | director"},
            "type": {"type": "string", "description": "dialogue | action | ooc | request | answer | note (+ narration | ruling for the DM)"},
            "body": {"type": "string", "description": "Message text (Markdown)."},
            "to": {**STR_LIST, "description": "Addressees: agent ids or groups (party, table, staff). Informational."},
            "awaits": {**STR_LIST, "description": "Agents who must respond before control returns to you. Each is woken."},
            "reply_to": {"type": "integer", "description": "Id of the message you are answering."},
            "spotlight": {**STR_LIST, "description": "DM only: agents whose reply runs at peak gear for free."},
        },
        "required": ["channel", "type", "body"],
    })
    async def post(args):
        try:
            msg = engine.post_message(agent, args["channel"], args["type"], args["body"],
                                      to=_list(args.get("to")), awaits=_list(args.get("awaits")),
                                      reply_to=args.get("reply_to"), spotlight=_list(args.get("spotlight")))
        except (engine.PostError, KeyError) as e:
            return err(str(e))
        ctx.posted.append(msg["id"])
        waits = f"; now awaiting {', '.join(msg['awaits'])}" if msg["awaits"] else ""
        return ok(f"Posted #{msg['id']:04d} to {args['channel']}{waits}.")
    tools.append(post)

    @tool("pass_turn", "Decline to act on everything currently awaiting you (posts a visible pass).",
          {"reason": str})
    async def pass_turn(args):
        ids = engine.pass_turn(agent, args["reason"])
        ctx.passed = True
        return ok(f"Passed on {', '.join(f'#{i:04d}' for i in ids) or 'nothing (nothing was awaiting you)'}.")
    tools.append(pass_turn)

    @tool("roll", "Roll dice publicly (result is posted by the system, so it is binding). "
                  "Expressions: d20+5, d20+3 adv, 4d6kh3, 2d8+1d6+3. DM may set secret=true.", {
        "type": "object",
        "properties": {
            "expr": {"type": "string"}, "reason": {"type": "string"},
            "channel": {"type": "string", "description": "Default: table"},
            "secret": {"type": "boolean", "description": "DM only: roll privately (logged, not posted)."},
        },
        "required": ["expr", "reason"],
    })
    async def roll(args):
        try:
            r = dice.roll(args["expr"])
        except dice.DiceError as e:
            return err(str(e))
        nat = f" (natural {r['natural']})" if r["natural"] in (1, 20) else ""
        line = f"🎲 {agent} rolls {r['expr']} for {args['reason']}: **{r['total']}**{nat} — {r['breakdown']}"
        engine.log("rolls", {"agent": agent, "reason": args["reason"], **r, "secret": bool(args.get("secret"))})
        if args.get("secret"):
            if role != "dm":
                return err("only the DM can roll in secret")
            return ok(line + " [secret, logged]")
        try:
            msg = engine.system_post(args.get("channel") or "table", "roll", line,
                                     extra={"roller": agent, "total": r["total"], "seed": r["seed"]})
        except engine.PostError as e:
            return err(str(e))
        return ok(f"{line} (posted as #{msg['id']:04d})")
    tools.append(roll)

    @tool("read_channel", "Read recent messages from a channel you belong to.", {
        "type": "object",
        "properties": {
            "channel": {"type": "string"},
            "since_id": {"type": "integer", "description": "Only messages after this id."},
            "limit": {"type": "integer", "description": "Max messages (default 30, newest kept)."},
            "chapter": {"type": "string", "description": "e.g. b1.c03 (default: current)."},
        },
        "required": ["channel"],
    })
    async def read_channel(args):
        agents = roster()
        st = state.load()
        ch = args["channel"]
        try:
            if not channels.can_read(ch, agent, role, agents):
                return err(f"you are not a member of '{ch}'")
            b, c = st["book"], st["chapter"]
            if args.get("chapter"):
                b, c = (int(x[1:]) for x in args["chapter"].split("."))
            msgs = channels.parse(channels.path_for(ch, st, agents, b, c))
        except (ValueError, IndexError) as e:
            return err(str(e))
        msgs = [m for m in msgs if m["id"] > (args.get("since_id") or 0)][-(args.get("limit") or 30):]
        return ok("\n".join(channels.short(m) for m in msgs) or "(no messages)")
    tools.append(read_channel)

    @tool("game_status", "Current book/chapter/scene, who is awaiting whom, your upshift charges.", {})
    async def game_status(args):
        with state.locked() as st:
            left = engine.charges_left(st, agent)
            snap = {k: st[k] for k in ("phase", "book", "chapter", "scene", "expectations", "human_waiting")}
        snap["your_upshift_charges"] = left
        snap["active_agents"] = {a: e["role"] for a, e in active(roster()).items()}
        return ok(yaml.safe_dump(snap, sort_keys=False, allow_unicode=True))
    tools.append(game_status)

    @tool("upshift", "Spend one upshift charge: this turn stops and is immediately re-run on your peak "
                     "model. Call it FIRST, before posting anything, and only for moments that matter.",
          {"reason": str})
    async def upshift(args):
        if ctx.posted:
            return err("you already posted this turn; upshift must be the first thing you do")
        try:
            left = engine.spend_charge(agent)
        except engine.PostError as e:
            return err(str(e))
        ctx.upshift_requested = True
        engine.log("gears", {"agent": agent, "event": "upshift", "reason": args["reason"], "left": left})
        return ok(f"Upshift granted ({left} left). End your turn NOW without posting; it will be replayed at peak gear.")
    tools.append(upshift)

    @tool("run_script", "Run an approved helper script from scripts/registry.yaml.",
          {"name": str, "args": str})
    async def run_script(args):
        reg = yaml.safe_load((ROOT / "scripts/registry.yaml").read_text()) or {}
        spec = (reg.get("scripts") or {}).get(args["name"])
        if not spec:
            return err(f"no approved script '{args['name']}'. Approved: {', '.join(reg.get('scripts') or {}) or 'none'}")
        if spec.get("roles") and role not in spec["roles"]:
            return err(f"script '{args['name']}' is not available to {role}")
        try:
            out = subprocess.run([sys.executable, str(ROOT / "scripts" / spec["file"]), *(args.get("args") or "").split()],
                                 capture_output=True, text=True, timeout=60, cwd=ROOT)
        except subprocess.TimeoutExpired:
            return err("script timed out")
        engine.log("scripts", {"agent": agent, "name": args["name"], "args": args.get("args"), "rc": out.returncode})
        return ok((out.stdout + (f"\n[stderr]\n{out.stderr}" if out.stderr else ""))[-8000:] or "(no output)")
    tools.append(run_script)

    # ------------------------------------------------------------------ DM
    if role == "dm":
        @tool("scene_start", "Open a new scene (posts a scene header at the table).", {
            "type": "object",
            "properties": {"title": {"type": "string"}, "location": {"type": "string"},
                           "cast": {**STR_LIST, "description": "Agent ids present (or 'party')."},
                           "place": {"type": "string", "description": "Key from library/places.yaml (for the map). Omit if none fits."}},
            "required": ["title", "location", "cast"],
        })
        async def scene_start(args):
            try:
                return ok(f"Scene {engine.scene_start(args['title'], args['location'], _list(args['cast']), args.get('place'))['id']} open.")
            except engine.PostError as e:
                return err(str(e))
        tools.append(scene_start)

        @tool("scene_end", "Close the open scene. Triggers the Author's draft, the Lore Keeper's extraction "
                           "and everyone's memory upkeep. Summary: 3-8 sentences of what happened and changed.",
              {"summary": str})
        async def scene_end(args):
            try:
                s = engine.scene_end(args["summary"])
            except engine.PostError as e:
                return err(str(e))
            return ok(f"Scene {s['id']} closed (#{s['start_id']:04d}–#{s['end_id']:04d}).")
        tools.append(scene_end)

        @tool("chapter_end", "End the current chapter (no scene may be open). The Author revises it.", {
            "type": "object",
            "properties": {"summary": {"type": "string"},
                           "next_book": {"type": "boolean", "description": "True if this was the book's last chapter."}},
            "required": ["summary"],
        })
        async def chapter_end(args):
            try:
                d = engine.chapter_end(args["summary"], bool(args.get("next_book")))
            except engine.PostError as e:
                return err(str(e))
            return ok(f"Book {d['book']} chapter {d['chapter']} closed with {len(d['scenes'])} scenes.")
        tools.append(chapter_end)

        @tool("update_sheet", "Patch a character sheet (deep merge; null removes a key). Posts the change at the table.", {
            "type": "object",
            "properties": {"character": {"type": "string"}, "patch": {"type": "object"}, "reason": {"type": "string"}},
            "required": ["character", "patch", "reason"],
        })
        async def update_sheet(args):
            try:
                engine.update_sheet(args["character"], args["patch"], args["reason"])
            except engine.PostError as e:
                return err(str(e))
            return ok("Sheet updated.")
        tools.append(update_sheet)

        @tool("grant_charge", "Award upshift charge(s) to an agent, like D&D Inspiration.",
              {"agent": str, "n": int, "reason": str})
        async def grant_charge(args):
            try:
                return ok(f"{args['agent']} now has {engine.grant_charge(args['agent'], args['n'], args['reason'])}.")
            except (engine.PostError, KeyError) as e:
                return err(str(e))
        tools.append(grant_charge)

    # ------------------------------------------------------------------ Director
    if role == "director":
        @tool("register_agent", "Add or update an agent in roster.yaml. Its folder agents/<id>/ must already "
                                "contain IDENTITY.md, SOUL.md and MEMORY.md (and sheet.yaml for player/npc).", {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "lowercase, a-z0-9-"},
                           "role": {"type": "string"}, "name": {"type": "string"},
                           "status": {"type": "string", "description": "active | benched | dead | retired"}},
            "required": ["id", "role", "name"],
        })
        async def register_agent(args):
            aid, r = args["id"], args["role"]
            if not aid.replace("-", "").isalnum() or aid != aid.lower():
                return err("id must be lowercase a-z, 0-9, '-'")
            if r not in ROLES or r in ("dm",):
                return err(f"role must be one of {', '.join(x for x in ROLES if x != 'dm')}")
            folder = ROOT / "agents" / aid
            need = ["IDENTITY.md", "SOUL.md", "MEMORY.md"] + (["sheet.yaml"] if r in ("player", "npc") else [])
            missing = [f for f in need if not (folder / f).exists()]
            if missing:
                return err(f"agents/{aid}/ is missing {', '.join(missing)}")
            agents = roster()
            agents[aid] = {"role": r, "name": args["name"], "status": args.get("status") or "active"}
            save_roster(agents)
            engine.system_post("director", "system", f"Registered {aid} ({r}): {args['name']} [{agents[aid]['status']}]")
            return ok(f"{aid} registered.")
        tools.append(register_agent)

        @tool("propose_script", "Submit scripts/pending/<file> for human approval (it cannot run until approved).",
              {"name": str, "file": str, "description": str, "roles": str})
        async def propose_script(args):
            if not (ROOT / "scripts/pending" / args["file"]).exists():
                return err(f"scripts/pending/{args['file']} does not exist")
            msg = engine.post_message(agent, "human", "request",
                                      f"Script proposal **{args['name']}** (`scripts/pending/{args['file']}`), "
                                      f"for roles: {args.get('roles') or 'all'}.\n\n{args['description']}\n\n"
                                      f"Approve with: `uv run arenya approve-script {args['file']} {args['name']} "
                                      f"--roles {args.get('roles') or ''}`", awaits=["human"])
            return ok(f"Proposal posted as #{msg['id']:04d}; the human will approve or reject it.")
        tools.append(propose_script)

    return create_sdk_mcp_server("arenya", tools=tools)
