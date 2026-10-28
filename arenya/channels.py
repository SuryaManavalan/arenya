"""Channel definitions, the on-disk message format, and parsing.

A channel file is plain Markdown; each message is:

    ### #0142 · dm → party · narration
    <!-- {"id": 142, "ts": "...", "from": "dm", ...} -->

    Body text...

The HTML comment holds the full metadata as one-line JSON and is the machine-readable source
of truth; the heading is for humans. Only engine.post_message writes these files.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import CHANNELS_DIR, OMNISCIENT_ROLES, active

HEADER_RE = re.compile(r"^### #(\d+) · ")
META_RE = re.compile(r"^<!-- (\{.*\}) -->$")

# scope: "chapter" -> channels/b<book>/c<chapter>/<name>.md
#        "book"    -> channels/b<book>/<name>.md
# post:  roles (or "self" for whispers) allowed to post. Readers = posters + omniscient roles.
STATIC_CHANNELS = {
    "table":     {"scope": "chapter", "post": ["dm", "player", "npc"],
                  "about": "In-character play. The game itself."},
    "ooc":       {"scope": "chapter", "post": ["dm", "player", "npc"],
                  "about": "Out-of-character table talk: rules questions, clarifications."},
    "backstage": {"scope": "book", "post": ["dm", "author", "lorekeeper", "director"],
                  "about": "Staff coordination: lore queries, author notes, logistics."},
    "human":     {"scope": "book", "post": ["dm", "author", "lorekeeper", "director", "human"],
                  "about": "Talking to the human (world creator)."},
    "director":  {"scope": "book", "post": ["dm", "player", "npc", "author", "lorekeeper", "director"],
                  "about": "Requests to the Director: new agents, new scripts, system problems."},
}
WHISPER = "whisper-"


def channel_def(name: str, agents: dict[str, dict]) -> dict:
    if name.startswith(WHISPER):
        target = name[len(WHISPER):]
        if agents.get(target, {}).get("role") not in ("player", "npc"):
            raise ValueError(f"no such whisper channel '{name}' (whispers exist for players/npcs)")
        return {"scope": "chapter", "post": ["dm", f"id:{target}"],
                "about": f"Private DM <-> {target}."}
    if name not in STATIC_CHANNELS:
        raise ValueError(f"no such channel '{name}'. Channels: {', '.join(all_channel_names(agents))}")
    return STATIC_CHANNELS[name]


def all_channel_names(agents: dict[str, dict]) -> list[str]:
    whispers = [WHISPER + a for a, e in agents.items() if e.get("role") in ("player", "npc")]
    return list(STATIC_CHANNELS) + whispers


def can_post(name: str, agent: str, role: str, agents: dict[str, dict]) -> bool:
    if agent == "system":
        return True
    post = channel_def(name, agents)["post"]
    return role in post or f"id:{agent}" in post


def can_read(name: str, agent: str, role: str, agents: dict[str, dict]) -> bool:
    return agent in ("human", "system") or role in OMNISCIENT_ROLES or can_post(name, agent, role, agents)


def expand_group(names: list[str], agents: dict[str, dict]) -> list[str]:
    """Expand group names: party (active players), table (dm + active players + npcs), staff."""
    act = active(agents)
    out: list[str] = []
    for n in names:
        if n == "party":
            out += [a for a, e in act.items() if e["role"] == "player"]
        elif n == "table":
            out += ["dm"] + [a for a, e in act.items() if e["role"] in ("player", "npc")]
        elif n == "staff":
            out += [a for a, e in act.items() if e["role"] in ("dm", "author", "lorekeeper", "director")]
        else:
            out.append(n)
    return list(dict.fromkeys(out))


def path_for(name: str, st: dict, agents: dict[str, dict], book: int | None = None,
             chapter: int | None = None) -> Path:
    scope = channel_def(name, agents)["scope"]
    b = book or st["book"]
    c = chapter or st["chapter"]
    base = CHANNELS_DIR / f"b{b}"
    return base / f"c{c:02d}" / f"{name}.md" if scope == "chapter" else base / f"{name}.md"


def render(msg: dict) -> str:
    to = ",".join(msg.get("to") or []) or "all"
    head = f"### #{msg['id']:04d} · {msg['from']} → {to} · {msg['type']}"
    meta = {k: v for k, v in msg.items() if k != "body" and v not in (None, [], "")}
    # "-->" inside a JSON string would end the comment early; > decodes back to ">".
    meta = json.dumps(meta, ensure_ascii=False).replace("-->", "--\\u003e")
    return f"{head}\n<!-- {meta} -->\n\n{msg['body'].rstrip()}\n\n"


def append(path: Path, msg: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# {path.stem} — {path.parent.relative_to(CHANNELS_DIR)}\n\n")
    with open(path, "a") as f:
        f.write(render(msg))


def parse(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    msgs: list[dict] = []
    cur: dict | None = None
    body: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if HEADER_RE.match(line) and i + 1 < len(lines) and (m := META_RE.match(lines[i + 1])):
            if cur is not None:
                cur["body"] = "\n".join(body).strip()
                msgs.append(cur)
            cur, body = json.loads(m.group(1)), []
            i += 2
            continue
        if cur is not None:
            body.append(line)
        i += 1
    if cur is not None:
        cur["body"] = "\n".join(body).strip()
        msgs.append(cur)
    return msgs


def all_messages(st: dict, books: list[int] | None = None) -> list[dict]:
    """Every message in the given books (default: current and previous), sorted by id."""
    books = books or sorted({max(1, st["book"] - 1), st["book"]})
    msgs: list[dict] = []
    for b in books:
        d = CHANNELS_DIR / f"b{b}"
        if d.exists():
            for p in d.rglob("*.md"):
                msgs += parse(p)
    return sorted(msgs, key=lambda m: m["id"])


def short(msg: dict) -> str:
    """One message as it appears inside a wake packet."""
    extra = []
    if msg.get("reply_to"):
        extra.append(f"re #{msg['reply_to']:04d}")
    if msg.get("awaits"):
        extra.append("awaits " + ",".join(msg["awaits"]))
    if msg.get("spotlight"):
        extra.append("spotlight " + ",".join(msg["spotlight"]))
    tail = f" ({'; '.join(extra)})" if extra else ""
    to = ",".join(msg.get("to") or []) or "all"
    return f"#{msg['id']:04d} [{msg['channel']}] {msg['from']} → {to} · {msg['type']}{tail}\n{msg['body']}\n"
