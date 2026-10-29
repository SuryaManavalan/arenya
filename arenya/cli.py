"""`uv run arenya <command>` — the human's control panel."""
from __future__ import annotations

import argparse
import asyncio
import shutil
import sys

import yaml

from . import channels, dice, engine, state
from .config import ROOT, roster, settings


def cmd_run(a):
    from .dispatcher import Dispatcher
    try:
        asyncio.run(Dispatcher(once=a.once, verbose=not a.quiet).run())
    except KeyboardInterrupt:
        print("\nstopped (in-flight jobs will be retried on next run)")


SEED_LIBRARY = (
    "Build the initial library from scratch, following rules/lorekeeper.md. Sources, in authority order: "
    "world/interviews/ (the human's own answers: canon), books/book1/chapters/ (human-written: canon), "
    "world/mechanics.md, plot/ (outline and DM notes: put secrets in library/restricted/), and every "
    "agents/*/IDENTITY.md. Create entries for every named character, place, organization, house, spirit "
    "and concept, plus timeline.md, canon-log.md and index.md. Characters' public entries hold only "
    "what's known in-world; secrets go to restricted/. Don't post unless you find a contradiction.")


def cmd_start(a):
    interviewed = any((ROOT / "world/interviews").glob("20*.md"))
    with state.locked() as st:
        if st["phase"] != "setup":
            sys.exit(f"already started (phase: {st['phase']})")
        st["phase"] = "onboarding"
        if interviewed:
            engine.enqueue(st, "lorekeeper", "task", {"title": "seed the library", "instructions": SEED_LIBRARY},
                           priority=0)
        engine.enqueue(st, "dm", "onboard", priority=1)
    print(("Library seeding + " if interviewed else "") + "DM onboarding queued. Now: uv run arenya run")


def cmd_status(a):
    with state.locked() as st:
        charges = {ag: engine.charges_left(st, ag) for ag in roster()}
        snap = st
    print(f"phase {snap['phase']} · book {snap['book']} chapter {snap['chapter']} · next id #{snap['next_id']:04d}"
          + (f" · PAUSED: {snap['pause_reason'] or 'by human'}" if snap["paused"] else ""))
    s = snap["scene"]
    print(f"scene: {s['id']} '{s['title']}' @ {s['location']} cast={','.join(s['cast'])}" if s else "scene: none open")
    print("awaiting human:", ", ".join(f"#{i:04d}" for i in snap["human_waiting"]) or "nothing")
    for e in snap["expectations"]:
        print(f"  #{e['id']:04d} {e['from']} in {e['channel']} waits on {', '.join(e['waiting_on'])}")
    print("queue:", ", ".join(f"{j['agent']}/{j['job']}" for j in sorted(snap["queue"], key=lambda j: (j['priority'], j['seq']))) or "empty")
    print("running:", ", ".join(f"{j['agent']}/{j['job']}" for j in snap["running"]) or "nothing")
    print("charges:", ", ".join(f"{k}={v}" for k, v in charges.items()))


def cmd_inbox(a):
    st = state.load()
    msgs = channels.parse(channels.path_for("human", st, roster()))
    if not a.all:
        msgs = [m for m in msgs if m["id"] in st["human_waiting"]] or msgs[-5:]
    for m in msgs:
        flag = "  <-- awaiting you" if m["id"] in st["human_waiting"] else ""
        print(channels.short(m) + flag + "\n")


def _body(a) -> str:
    if a.file:
        return open(a.file).read()
    if a.text == ["-"]:
        return sys.stdin.read()
    return " ".join(a.text)


def cmd_reply(a):
    m = engine.post_message("human", "human", "answer", _body(a), reply_to=a.id, to=a.to or [])
    print(f"posted #{m['id']:04d}")


def cmd_say(a):
    m = engine.post_message("human", a.channel, a.type, _body(a), to=a.to or [], awaits=a.awaits or [])
    print(f"posted #{m['id']:04d} in {a.channel}")


def cmd_pause(a, value=True):
    with state.locked() as st:
        st["paused"] = value
        st["pause_reason"] = None if not value else (a.reason or "by human")
        if not value:
            st["idle_wakes"] = 0
    print("paused" if value else "resumed")


def cmd_approve_script(a):
    src = ROOT / "scripts/pending" / a.file
    if not src.exists():
        sys.exit(f"no such file {src}")
    print(src.read_text())
    if input(f"\nApprove {a.file} as '{a.name}'? [y/N] ").lower() != "y":
        return
    shutil.move(src, ROOT / "scripts" / a.file)
    reg_path = ROOT / "scripts/registry.yaml"
    reg = yaml.safe_load(reg_path.read_text()) or {}
    reg.setdefault("scripts", {})[a.name] = {"file": a.file, "roles": a.roles or [],
                                             "description": a.description or ""}
    reg_path.write_text(yaml.safe_dump(reg, sort_keys=False))
    engine.post_message("human", "director", "decree", f"Approved script `{a.name}` ({a.file}).")
    print("approved")


def cmd_cost(a):
    import collections
    import json
    path = ROOT / "logs/usage.jsonl"
    if not path.exists():
        sys.exit("no usage logged yet")
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    by = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        key = r["agent"] if a.by == "agent" else f"{r['agent']}/{r['job']}" if a.by == "job" else r["model"]
        by[key][0] += r.get("cost_usd") or 0
        by[key][1] += 1
    total = sum(v[0] for v in by.values())
    for k, (c, n) in sorted(by.items(), key=lambda kv: -kv[1][0]):
        print(f"{k:28} {n:5} turns  ${c:8.2f}  {100 * c / total if total else 0:5.1f}%")
    st = state.load()
    print(f"{'TOTAL':28} {len(rows):5} turns  ${total:8.2f}   (API-price estimate; on a subscription "
          f"this is usage, not billing)")
    if st["scenes"]:
        print(f"closed scenes: {len(st['scenes'])} → ${total / len(st['scenes']):.2f} per scene")


def cmd_set_chapter(a):
    with state.locked() as st:
        if st["scene"]:
            sys.exit("close the open scene first")
        st["book"], st["chapter"], st["scene_counter"] = a.book, a.chapter, 0
    print(f"now at book {a.book}, chapter {a.chapter}")


def cmd_roll(a):
    r = dice.roll(" ".join(a.expr))
    print(f"{r['total']}  ({r['breakdown']})")


def cmd_tail(a):
    st = state.load()
    for m in channels.parse(channels.path_for(a.channel, st, roster()))[-a.n:]:
        print(channels.short(m))


def main():
    p = argparse.ArgumentParser(prog="arenya", description="Multi-agent D&D → novel engine")
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("run", help="run the dispatcher (Ctrl-C to stop)")
    s.add_argument("--once", action="store_true", help="exit when the queue drains")
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(f=cmd_run)
    sub.add_parser("start", help="begin: queue the DM's onboarding interview").set_defaults(f=cmd_start)
    sub.add_parser("status", help="phase, scene, who waits on whom, queue, charges").set_defaults(f=cmd_status)
    s = sub.add_parser("inbox", help="messages awaiting you in the human channel")
    s.add_argument("--all", action="store_true")
    s.set_defaults(f=cmd_inbox)

    for name, fn in (("reply", cmd_reply), ("say", cmd_say)):
        s = sub.add_parser(name, help="answer a message in the human channel" if name == "reply"
                           else "post anywhere as the human (type decree = binding world fact)")
        if name == "reply":
            s.add_argument("id", type=int)
        else:
            s.add_argument("channel")
            s.add_argument("--type", default="note")
            s.add_argument("--awaits", nargs="*")
        s.add_argument("text", nargs="*")
        s.add_argument("--file", help="read the body from a file")
        s.add_argument("--to", nargs="*")
        s.set_defaults(f=fn)

    s = sub.add_parser("pause")
    s.add_argument("reason", nargs="?")
    s.set_defaults(f=cmd_pause)
    sub.add_parser("resume").set_defaults(f=lambda a: cmd_pause(a, False))

    s = sub.add_parser("approve-script", help="review & approve a Director-proposed script")
    s.add_argument("file")
    s.add_argument("name")
    s.add_argument("--roles", nargs="*")
    s.add_argument("--description")
    s.set_defaults(f=cmd_approve_script)

    s = sub.add_parser("cost", help="estimated spend from logs/usage.jsonl")
    s.add_argument("--by", choices=["agent", "job", "model"], default="job")
    s.set_defaults(f=cmd_cost)

    s = sub.add_parser("set-chapter", help="set where play starts/continues (e.g. after human-written chapters)")
    s.add_argument("book", type=int)
    s.add_argument("chapter", type=int)
    s.set_defaults(f=cmd_set_chapter)

    s = sub.add_parser("roll", help="roll dice locally (not posted)")
    s.add_argument("expr", nargs="+")
    s.set_defaults(f=cmd_roll)
    s = sub.add_parser("tail", help="show the last N messages of a channel")
    s.add_argument("channel")
    s.add_argument("-n", type=int, default=20)
    s.set_defaults(f=cmd_tail)

    a = p.parse_args()
    try:
        a.f(a)
    except engine.PostError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
