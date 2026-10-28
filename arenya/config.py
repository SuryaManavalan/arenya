"""Paths, config and roster loading."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
LOGS_DIR = ROOT / "logs"
CHANNELS_DIR = ROOT / "channels"

ROLES = ("dm", "player", "npc", "author", "lorekeeper", "director")
STAFF_ROLES = ("dm", "author", "lorekeeper", "director")
# Roles that may read every channel and every file (narrators/archivists of the whole game).
OMNISCIENT_ROLES = ("dm", "author", "lorekeeper", "director")


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def settings() -> dict:
    return load_yaml(ROOT / "arenya.yaml")


def roster() -> dict[str, dict]:
    """Agent id -> entry. Re-read on every call: the Director edits it while the game runs."""
    return load_yaml(ROOT / "roster.yaml").get("agents", {}) or {}


def save_roster(agents: dict[str, dict]) -> None:
    path = ROOT / "roster.yaml"
    header = "# Agent registry. Maintained by the Director (register_agent) and by hand.\n"
    path.write_text(header + yaml.safe_dump({"agents": agents}, sort_keys=False, allow_unicode=True))


def active(agents: dict[str, dict]) -> dict[str, dict]:
    return {k: v for k, v in agents.items() if v.get("status", "active") == "active"}


def role_of(agent_id: str) -> str:
    if agent_id in ("human", "system"):
        return agent_id
    entry = roster().get(agent_id)
    if not entry:
        raise KeyError(f"unknown agent '{agent_id}'")
    return entry["role"]


def gear(n: int) -> dict:
    gears = settings()["gears"]
    n = max(min(gears), min(n, max(gears)))
    return {"n": n, **gears[n]}
