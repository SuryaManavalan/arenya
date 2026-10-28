"""Engine state: one JSON file guarded by an flock so the dispatcher and the CLI can both write it.

Never hold `locked()` across an await, and never nest it: flock is per open file, so a nested
lock in the same process deadlocks.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
from datetime import datetime, timezone

from .config import STATE_DIR

STATE_FILE = STATE_DIR / "state.json"
LOCK_FILE = STATE_DIR / ".lock"


def fresh() -> dict:
    return {
        "phase": "setup",          # setup -> onboarding -> play
        "next_id": 1,              # global message id counter (unique across all channels)
        "book": 1,
        "chapter": 1,
        "scene_counter": 0,        # scenes started in the current chapter
        "scene": None,             # {"id","title","location","cast","start_id","spotlights_used"}
        "scenes": [],              # closed scenes: {"id","title","start_id","end_id","summary"}
        "expectations": [],        # {"id","from","channel","waiting_on":[...],"ts"}
        "cursors": {},             # agent -> last global message id it has been shown
        "sessions": {},            # agent -> {"key","session_id"}
        "charges": {},             # agent -> {"period":"b1.c04","left":n}
        "grants_used": {},         # period -> n (DM-awarded charges)
        "upshift": [],             # agents whose next turn runs at peak gear
        "spotlight": [],           # agents whose next turn is a free peak-gear turn
        "queue": [],               # pending jobs (see dispatcher.Job)
        "running": [],             # jobs in flight (re-queued if the dispatcher dies)
        "job_seq": 0,
        "human_waiting": [],       # message ids awaiting the human
        "idle_wakes": 0,
        "paused": False,
        "pause_reason": None,
    }


def load() -> dict:
    if not STATE_FILE.exists():
        return fresh()
    st = json.loads(STATE_FILE.read_text())
    for k, v in fresh().items():
        st.setdefault(k, v)
    return st


def _save(st: dict) -> None:
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1))
    os.replace(tmp, STATE_FILE)


@contextlib.contextmanager
def locked():
    """Exclusive read-modify-write of state.json. Yields the state dict; saved on clean exit."""
    STATE_DIR.mkdir(exist_ok=True)
    with open(LOCK_FILE, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        st = load()
        yield st
        _save(st)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def period(st: dict) -> str:
    """Charge/grant accounting period: the current chapter."""
    return f"b{st['book']}.c{st['chapter']:02d}"


def chapter_key(st: dict) -> str:
    return period(st)
