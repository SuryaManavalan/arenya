"""System prompts (stable, cacheable) and wake packets (per turn)."""
from __future__ import annotations

from . import channels, state
from .config import ROOT, roster, settings

STAFF_CHANNELS = {"backstage", "human", "director"}


def _read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text().strip() if p.exists() else ""


def system_prompt(agent: str, role: str) -> str:
    rule_files = ["rules/common.md", "rules/messaging.md", f"rules/{role}.md"]
    if role == "npc":
        rule_files.insert(2, "rules/player.md")
    parts = [_read(f) for f in rule_files]
    parts.append(f"# Who you are\n\nYour agent id is `{agent}`. Your folder is `agents/{agent}/`.")
    for f in ("IDENTITY.md", "SOUL.md"):
        parts.append(_read(f"agents/{agent}/{f}"))
    return "\n\n---\n\n".join(p for p in parts if p)


def session_key(st: dict, job: str, args: dict) -> str | None:
    """Turns and reflections share one session per scene; other jobs start fresh."""
    if job in ("turn", "nudge", "replay"):
        return (st.get("scene") or {}).get("id") or f"{state.chapter_key(st)}.between"
    if job == "reflect":
        return args["scene"]["id"]
    return None


def _scene_line(st: dict) -> str:
    s = st.get("scene")
    where = f"Book {st['book']}, Chapter {st['chapter']}"
    if not s:
        return f"{where} · no scene open (phase: {st['phase']})"
    return f"{where} · Scene {s['id']} \"{s['title']}\" at {s['location']} · cast: {', '.join(s['cast'])}"


def _relevant(msg: dict, agent: str, role: str, agents: dict) -> bool:
    if not channels.can_read(msg["channel"], agent, role, agents):
        return False
    if role in ("author", "lorekeeper", "director"):
        # They read the table from files on their own jobs; turns only surface what concerns them.
        return msg["channel"] in STAFF_CHANNELS or agent in (msg.get("to") or []) or agent in (msg.get("awaits") or [])
    return True


def wake_packet(st: dict, agent: str, role: str, job: str, args: dict, gear: dict, why: str,
                charges: int, new_session: bool) -> tuple[str, int]:
    """Build the turn prompt. Returns (prompt, new cursor)."""
    agents = roster()
    cursor = st["cursors"].get(agent, 0)
    head = [f"# Wake: {job}", _scene_line(st),
            f"Gear {gear['n']} ({gear['model']}, effort {gear['effort']}) — {why}. Upshift charges left this chapter: {charges}."]

    if job == "replay":
        return "\n".join(head + ["", "Your upshift went through. You are now on your peak model. "
                                     "Take the turn you were about to take, with everything you've got."]), cursor
    if job == "nudge":
        owed = [e for e in st["expectations"] if agent in e["waiting_on"]]
        ids = ", ".join(f"#{e['id']:04d} in {e['channel']}" for e in owed)
        return "\n".join(head + ["", f"Your turn ended but you still owe a response to {ids}. "
                                     "Post in that channel (or reply_to it), or call pass_turn."]), cursor

    body: list[str] = []
    if new_session and job in ("turn", "onboard"):
        mem = _read(f"agents/{agent}/MEMORY.md")
        body += ["## Your MEMORY.md", mem or "(empty)", ""]

    if job in ("turn", "onboard"):
        all_msgs = channels.all_messages(st)
        new = [m for m in all_msgs if m["id"] > cursor and m["from"] != agent and _relevant(m, agent, role, agents)]
        limit = settings()["packet_message_limit"]
        owed = [e for e in st["expectations"] if agent in e["waiting_on"]]
        by_id = {m["id"]: m for m in all_msgs}
        if owed:
            body.append("## Awaiting your response")
            for e in owed:
                m = by_id.get(e["id"])
                body.append(f"- #{e['id']:04d} from {e['from']} in **{e['channel']}**"
                            + (f": {m['body'][:300]}" if m else ""))
            body.append("")
        mine = [e for e in st["expectations"] if e["from"] == agent]
        if mine:
            body.append("## You are still waiting on")
            body += [f"- #{e['id']:04d} in {e['channel']}: {', '.join(e['waiting_on'])}" for e in mine]
            body.append("")
        if new:
            skipped = max(0, len(new) - limit)
            body.append(f"## New since your last turn ({len(new)} messages"
                        + (f"; oldest {skipped} omitted — use read_channel" if skipped else "") + ")")
            body += [channels.short(m) for m in new[-limit:]]
        elif not owed and job == "turn":
            body.append("## The table is quiet\nNo one is awaiting anyone. " + (
                "Advance the story: narrate, prompt the party, open or close a scene." if role == "dm"
                else "Nothing needs you right now; end your turn unless you have something to add."))
        cursor = max([cursor] + [m["id"] for m in all_msgs])

    if job == "onboard":
        body += ["", "## Job: onboarding interview",
                 "Follow rules/dm.md § Onboarding. Read plot/, world/, library/ and books/ first, then interview "
                 "the human in the `human` channel (always await human). Onboarding ends when you open the first scene."]
    elif job == "draft":
        s = args["scene"]
        out = f"books/book{s['book']}/drafts/c{s['chapter']:02d}/s{s['id'].split('.s')[1]}.md"
        body += ["## Job: draft scene", f"Scene {s['id']} \"{s['title']}\" at {s['location']}; cast {', '.join(s['cast'])}.",
                 f"Source: messages #{s['start_id']:04d}–#{s['end_id']:04d} in channels/b{s['book']}/c{s['chapter']:02d}/ "
                 "(table.md, ooc.md, whisper-*.md) and any backstage/human messages in that range.",
                 f"DM summary: {s['summary']}", f"Write the draft to `{out}` following rules/author.md § Drafts."]
    elif job == "revise":
        b, c = args["book"], args["chapter"]
        body += ["## Job: revise chapter", f"Book {b}, Chapter {c} is finished. DM summary: {args['summary']}",
                 f"Drafts: books/book{b}/drafts/c{c:02d}/. Write the finished chapter to `books/book{b}/chapters/c{c:02d}.md` "
                 "following rules/author.md § Revision." + (" This is the book's final chapter." if args.get("final_in_book") else "")]
    elif job == "extract":
        s = args["scene"]
        body += ["## Job: extract canon", f"Scene {s['id']} \"{s['title']}\" (#{s['start_id']:04d}–#{s['end_id']:04d}) "
                 f"in channels/b{s['book']}/c{s['chapter']:02d}/. DM summary: {s['summary']}",
                 "Update library/ following rules/lorekeeper.md § Extraction."]
    elif job == "reflect":
        s = args["scene"]
        body += ["## Job: memory upkeep", f"Scene {s['id']} \"{s['title']}\" just ended. DM summary: {s['summary']}",
                 f"Rewrite agents/{agent}/MEMORY.md following rules/common.md § Memory. Do not post anything."]
    elif job == "turn":
        body += ["", "## Your move", "Act through your tools. Answer everything awaiting you (post in that channel, "
                 "reply_to it, or pass_turn). Then end your turn — no closing summary needed."]
    return "\n".join(head + [""] + body), cursor
