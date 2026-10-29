"""Game engine: the only code that writes channels and mutates game state.

Called by the MCP tools (agents), the dispatcher, and the CLI (human). Every public function
takes the state lock itself, so callers must not already hold it.

Turn-taking model ("expectations"):
  * A post with awaits=[a, b] creates an expectation owned by the poster.
  * Each awaited agent is queued for a turn.
  * An awaited agent satisfies it by posting in the same channel, replying to it (reply_to),
    or calling pass_turn.
  * When nobody is left in waiting_on, the owner is queued for a turn.
  * Awaiting "human" never queues anything; it pauses that thread until `arenya reply`.
"""
from __future__ import annotations

import json
import os
import subprocess

from . import channels, state
from .config import LOGS_DIR, ROOT, active, role_of, roster, settings

AGENT_TYPES = {"dialogue", "action", "ooc", "request", "answer", "note"}
DM_TYPES = AGENT_TYPES | {"narration", "ruling"}
HUMAN_TYPES = AGENT_TYPES | {"narration", "ruling", "decree"}
SYSTEM_TYPES = {"roll", "sheet", "pass", "scene_start", "scene_end", "chapter_end", "system"}

WORLD_TURN = {"title": "world turn: advance the fronts",
              "instructions": "Follow rules/dm.md § Fronts and the world turn. Read plot/fronts.md, decide what each "
                              "front did off-screen since its last advance, update fronts.md (step, what, where, when), "
                              "plan the visible signs, and tidy plot/dm-notes.md (finished scene logs go to plot/dm-log.md). "
                              "Don't post at the table."}

PRIORITY = {"dm": 0, "player": 1, "npc": 1, "director": 2, "lorekeeper": 3, "author": 4}


class PostError(ValueError):
    pass


# --------------------------------------------------------------------------- posting

def post_message(sender: str, channel: str, type_: str, body: str, *, to: list[str] | None = None,
                 awaits: list[str] | None = None, reply_to: int | None = None,
                 spotlight: list[str] | None = None, extra: dict | None = None) -> dict:
    agents = roster()
    role = role_of(sender)
    allowed = {"dm": DM_TYPES, "human": HUMAN_TYPES, "system": SYSTEM_TYPES | DM_TYPES}.get(role, AGENT_TYPES)
    if type_ not in allowed:
        raise PostError(f"type '{type_}' not allowed for {role}. Allowed: {', '.join(sorted(allowed))}")
    if not body or not body.strip():
        raise PostError("empty body")
    if any(channels.HEADER_RE.match(l) for l in body.splitlines()):
        raise PostError("body lines may not start with '### #' (reserved for message headers)")
    try:
        channels.channel_def(channel, agents)
    except ValueError as e:
        raise PostError(str(e))
    if not channels.can_post(channel, sender, role, agents):
        raise PostError(f"{sender} ({role}) cannot post in '{channel}'")

    to = channels.expand_group(to or [], agents)
    awaits = channels.expand_group(awaits or [], agents)
    if type_ == "request" and not awaits:
        awaits = [t for t in to if t != sender]
    awaits = [a for a in awaits if a != sender]
    act = active(agents)
    for a in awaits:
        if a == "human":
            if channel != "human":
                raise PostError("you can only await the human in the 'human' channel")
            continue
        if a not in act:
            raise PostError(f"cannot await '{a}': not an active agent")
        if not channels.can_post(channel, a, act[a]["role"], agents):
            raise PostError(f"cannot await '{a}' in '{channel}': they can't post there")
    for t in to:
        if t not in agents and t not in ("human", "all"):
            raise PostError(f"unknown recipient '{t}'")
    spotlight = channels.expand_group(spotlight or [], agents)
    if spotlight and role not in ("dm", "human"):
        raise PostError("only the DM can put agents in the spotlight")

    with state.locked() as st:
        # Answering an expectation already hands control back to its owner when it completes;
        # also awaiting the owner would wake them early (before everyone else has answered).
        owners = {e["from"] for e in st["expectations"] if sender in e["waiting_on"]
                  and (e["channel"] == channel or e["id"] == reply_to)}
        awaits = [a for a in awaits if a not in owners]
        if spotlight and role == "dm":
            scene = st.get("scene") or {}
            used = scene.get("spotlights_used", 0)
            if used + len(spotlight) > settings()["spotlights_per_scene"]:
                raise PostError(f"spotlight budget for this scene exhausted ({used} used)")
            if scene:
                scene["spotlights_used"] = used + len(spotlight)
        msg = {
            "id": st["next_id"], "ts": state.now(), "from": sender, "channel": channel,
            "type": type_, "to": to, "awaits": awaits, "reply_to": reply_to,
            "spotlight": spotlight, "scene": (st.get("scene") or {}).get("id"),
            "chapter": state.chapter_key(st), **(extra or {}), "body": body.strip(),
        }
        st["next_id"] += 1
        channels.append(channels.path_for(channel, st, agents), msg)
        _resolve(st, sender, msg)
        for a in spotlight:
            if a not in st["spotlight"]:
                st["spotlight"].append(a)
        if awaits:
            st["expectations"].append({"id": msg["id"], "from": sender, "channel": channel,
                                       "waiting_on": list(awaits), "ts": msg["ts"]})
            for a in awaits:
                if a == "human":
                    st["human_waiting"].append(msg["id"])
                else:
                    enqueue(st, a, "turn")
        if sender != "system" and role != "human":
            st["idle_wakes"] = 0
    if "human" in awaits:
        notify_human(f"#{msg['id']:04d} from {sender}: {body.strip()[:200]}")
    return msg


def _resolve(st: dict, sender: str, msg: dict | None, pass_all: bool = False) -> None:
    """Remove `sender` from expectations this message (or a pass) satisfies."""
    keep = []
    for exp in st["expectations"]:
        if sender in exp["waiting_on"] and (
            pass_all
            or (msg and msg["id"] > exp["id"] and (msg["channel"] == exp["channel"] or msg.get("reply_to") == exp["id"]))
        ):
            exp["waiting_on"].remove(sender)
            if sender == "human" and exp["id"] in st["human_waiting"]:
                st["human_waiting"].remove(exp["id"])
        if exp["waiting_on"]:
            keep.append(exp)
        elif exp["from"] not in ("human", "system"):
            enqueue(st, exp["from"], "turn")
    st["expectations"] = keep


def pass_turn(agent: str, reason: str) -> list[int]:
    """Agent declines to act. Posts a visible pass in each channel it was awaited in."""
    with state.locked() as st:
        pending = [e for e in st["expectations"] if agent in e["waiting_on"]]
    for exp in pending:
        post_message("system", exp["channel"], "pass", f"{agent} passes: {reason}", reply_to=exp["id"])
    with state.locked() as st:
        _resolve(st, agent, None, pass_all=True)
    return [e["id"] for e in pending]


def system_post(channel: str, type_: str, body: str, **kw) -> dict:
    return post_message("system", channel, type_, body, **kw)


def waiting_on(agent: str) -> list[dict]:
    st = state.load()
    return [e for e in st["expectations"] if agent in e["waiting_on"]]


# --------------------------------------------------------------------------- queue

def enqueue(st: dict, agent: str, job: str, args: dict | None = None, priority: int | None = None) -> None:
    """Queue a job (caller holds the lock). Turn jobs coalesce: one pending turn per agent."""
    entry = roster().get(agent)
    if not entry or entry.get("status", "active") != "active":
        return
    if job == "turn" and any(j["agent"] == agent and j["job"] == "turn" for j in st["queue"]):
        return
    st["job_seq"] += 1
    pr = priority if priority is not None else PRIORITY.get(entry["role"], 5) + (0 if job == "turn" else 5)
    st["queue"].append({"seq": st["job_seq"], "agent": agent, "job": job, "args": args or {},
                        "priority": pr, "attempt": 0, "ts": state.now()})


def enqueue_locked(agent: str, job: str, args: dict | None = None, priority: int | None = None) -> None:
    with state.locked() as st:
        enqueue(st, agent, job, args, priority)


# --------------------------------------------------------------------------- scenes & chapters

def scene_start(title: str, location: str, cast: list[str], place: str | None = None) -> dict:
    agents = roster()
    cast = channels.expand_group(cast, agents)
    with state.locked() as st:
        if st.get("scene"):
            raise PostError(f"scene {st['scene']['id']} is still open; end it first")
        st["scene_counter"] += 1
        sid = f"b{st['book']}.c{st['chapter']:02d}.s{st['scene_counter']:02d}"
        st["scene"] = {"id": sid, "title": title, "location": location, "cast": cast, "place": place,
                       "start_id": st["next_id"], "spotlights_used": 0}
        for a in cast:   # last known whereabouts, for the dashboard map
            st.setdefault("locations", {})[a] = {"place": place, "location": location, "scene": sid}
        if st["phase"] != "play":
            st["phase"] = "play"
    system_post("table", "scene_start", f"**Scene {sid} — {title}**\nLocation: {location}\nCast: {', '.join(cast)}",
                extra={"scene_title": title})
    return {"id": sid}


def scene_end(summary: str) -> dict:
    with state.locked() as st:
        scene = st.get("scene")
        if not scene:
            raise PostError("no scene is open")
    msg = system_post("table", "scene_end", f"**End of scene {scene['id']} — {scene['title']}**\n\n{summary}")
    with state.locked() as st:
        closed = {"id": scene["id"], "title": scene["title"], "location": scene["location"],
                  "place": scene.get("place"),
                  "cast": scene["cast"], "start_id": scene["start_id"], "end_id": msg["id"],
                  "summary": summary, "book": st["book"], "chapter": st["chapter"]}
        st["scenes"].append(closed)
        st["scene"] = None
        st["spotlight"] = []
        enqueue(st, "author", "draft", {"scene": closed})
        in_chapter = sum(1 for s in st["scenes"] if s["book"] == st["book"] and s["chapter"] == st["chapter"])
        if in_chapter % 3 == 0:
            enqueue(st, "dm", "task", WORLD_TURN, priority=2)
        enqueue(st, "lorekeeper", "extract", {"scene": closed})
        for a in dict.fromkeys(["dm", *closed["cast"]]):
            enqueue(st, a, "reflect", {"scene": closed})
    return closed


def chapter_end(summary: str, next_book: bool = False) -> dict:
    with state.locked() as st:
        if st.get("scene"):
            raise PostError("close the open scene before ending the chapter")
        done = {"book": st["book"], "chapter": st["chapter"],
                "scenes": [s for s in st["scenes"] if s["book"] == st["book"] and s["chapter"] == st["chapter"]]}
    system_post("table", "chapter_end", f"**End of Book {done['book']}, Chapter {done['chapter']}**\n\n{summary}")
    with state.locked() as st:
        enqueue(st, "author", "revise", {"book": done["book"], "chapter": done["chapter"],
                                         "summary": summary, "final_in_book": next_book})
        enqueue(st, "dm", "task", WORLD_TURN, priority=2)
        if next_book:
            st["book"] += 1
            st["chapter"] = 1
        else:
            st["chapter"] += 1
        st["scene_counter"] = 0
    return done


# --------------------------------------------------------------------------- gears & charges

def charges_left(st: dict, agent: str) -> int:
    """Charges for the current chapter, topping up when a new chapter starts."""
    role = role_of(agent)
    cfg = settings()["roles"][role]
    rec = st["charges"].get(agent)
    p = state.period(st)
    if not rec:
        rec = {"period": p, "left": cfg["charges"]}
    elif rec["period"] != p:
        rec = {"period": p, "left": min(cfg["charge_cap"], rec["left"] + cfg["charges"])}
    st["charges"][agent] = rec
    return rec["left"]


def spend_charge(agent: str) -> int:
    with state.locked() as st:
        left = charges_left(st, agent)
        if left <= 0:
            raise PostError("no upshift charges left this chapter")
        st["charges"][agent]["left"] = left - 1
        if agent not in st["upshift"]:
            st["upshift"].append(agent)
        return left - 1


def grant_charge(agent: str, n: int, reason: str) -> int:
    role = role_of(agent)
    cap = settings()["roles"][role]["charge_cap"]
    with state.locked() as st:
        p = state.period(st)
        used = st["grants_used"].get(p, 0)
        if used + n > settings()["grants_per_chapter"]:
            raise PostError(f"grant budget exhausted this chapter ({used} used)")
        left = charges_left(st, agent)
        st["charges"][agent]["left"] = min(cap, left + n)
        st["grants_used"][p] = used + n
        new = st["charges"][agent]["left"]
    system_post("ooc", "system", f"The DM grants {agent} {n} upshift charge(s): {reason} (now {new}).")
    return new


def pick_gear(st: dict, agent: str, job: str) -> tuple[int, str]:
    """Return (gear number, why). Consumes pending upshift/spotlight flags (caller holds lock)."""
    role = role_of(agent)
    cfg = settings()["roles"][role]
    pinned = settings().get("job_gears", {}).get(job)
    if job == "task":
        pinned = None
    if pinned is not None:
        return pinned, f"{job} job"
    if agent in st["spotlight"]:
        st["spotlight"].remove(agent)
        return cfg["peak_gear"], "spotlight"
    if agent in st["upshift"]:
        st["upshift"].remove(agent)
        return cfg["peak_gear"], "upshift charge"
    return cfg["base_gear"], "base"


# --------------------------------------------------------------------------- sheets

def update_sheet(character: str, patch: dict, reason: str) -> dict:
    import yaml
    path = ROOT / "agents" / character / "sheet.yaml"
    if not path.exists():
        raise PostError(f"{character} has no sheet.yaml")
    sheet = yaml.safe_load(path.read_text()) or {}
    changes: list[str] = []

    def merge(dst: dict, src: dict, prefix: str = "") -> None:
        for k, v in src.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                merge(dst[k], v, f"{prefix}{k}.")
            elif v is None:
                if k in dst:
                    changes.append(f"{prefix}{k}: {dst.pop(k)} → (removed)")
            else:
                changes.append(f"{prefix}{k}: {dst.get(k)} → {v}")
                dst[k] = v

    merge(sheet, patch)
    path.write_text(yaml.safe_dump(sheet, sort_keys=False, allow_unicode=True))
    system_post("table", "sheet", f"{character}: " + "; ".join(changes) + f" ({reason})")
    return sheet


# --------------------------------------------------------------------------- human & logs

def notify_human(text: str) -> None:
    print(f"\a\n>>> HUMAN NEEDED: {text}\n    reply with: uv run arenya reply <id> \"...\"\n", flush=True)
    cmd = settings().get("notify_command")
    if cmd:
        subprocess.Popen(cmd, shell=True, env={**os.environ, "ARENYA_MSG": text})


def log(name: str, record: dict) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    with open(LOGS_DIR / f"{name}.jsonl", "a") as f:
        f.write(json.dumps({"ts": state.now(), **record}, ensure_ascii=False) + "\n")
