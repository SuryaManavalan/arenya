"""Per-role file access control, enforced by a PreToolUse hook on the built-in file tools.

Patterns are fnmatch globs relative to the repo root ("*" also matches "/"). "{self}" is the
agent's id. Deny rules beat allow rules. Channel files are only readable by omniscient roles;
everyone else reads channels through the read_channel tool, which filters by membership.
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from .config import ROOT

ENGINE_OWNED = ["state/**", "logs/**", "channels/**", "arenya/**", "arenya.yaml", "roster.yaml",
                "rules/**", "scripts/*.py", "scripts/registry.yaml", ".venv/**", ".git/**", "docs/**",
                "pyproject.toml", "uv.lock"]

PLAYER_READ = ["rules/common.md", "rules/messaging.md", "rules/player.md", "world/**",
               "library/public/**", "agents/{self}/**", "agents/*/IDENTITY.md", "scripts/registry.yaml"]

READ: dict[str, list[str]] = {
    "dm": ["**"],
    "author": ["**"],
    "lorekeeper": ["**"],
    "director": ["**"],
    "player": PLAYER_READ,
    "npc": PLAYER_READ,
}
READ_DENY: dict[str, list[str]] = {
    "dm": ["state/**", ".venv/**", ".git/**"],
    "author": ["state/**", ".venv/**", ".git/**"],
    "lorekeeper": ["state/**", ".venv/**", ".git/**"],
    "director": [".venv/**", ".git/**"],
}
WRITE: dict[str, list[str]] = {
    "dm": ["plot/**", "world/**", "agents/dm/**"],
    "author": ["books/**", "agents/author/**"],
    "lorekeeper": ["library/**", "agents/lorekeeper/**"],
    "director": ["agents/**", "scripts/pending/**"],
    "player": ["agents/{self}/MEMORY.md", "agents/{self}/notes.md"],
    "npc": ["agents/{self}/MEMORY.md", "agents/{self}/notes.md"],
}
# Sheets change only through the DM's update_sheet tool, so the change is logged at the table.
WRITE_DENY_ALL = ENGINE_OWNED + ["agents/*/sheet.yaml"]

FILE_TOOLS = "Read|Write|Edit|MultiEdit|Glob|Grep|NotebookEdit"


def _match(rel: str, patterns: list[str], agent: str) -> bool:
    return any(fnmatch.fnmatch(rel, p.replace("{self}", agent)) for p in patterns)


def _rel(path: str) -> str | None:
    """Repo-relative path, or None if it escapes the repo."""
    p = Path(path)
    full = Path(os.path.realpath(p if p.is_absolute() else ROOT / p))
    try:
        return full.relative_to(ROOT).as_posix() or "."
    except ValueError:
        return None


def can_read(agent: str, role: str, path: str) -> bool:
    rel = _rel(path)
    if rel is None:
        return False
    return _match(rel, READ.get(role, []), agent) and not _match(rel, READ_DENY.get(role, []), agent)


def can_read_dir(agent: str, role: str, path: str) -> bool:
    """A directory may be searched only if everything beneath it is readable."""
    rel = _rel(path)
    if rel is None:
        return False
    probe = "__probe__" if rel == "." else f"{rel}/__probe__"
    if READ.get(role) == ["**"]:
        return not any(fnmatch.fnmatch(rel, p.rstrip("/*")) for p in READ_DENY.get(role, []))
    return _match(probe, READ.get(role, []), agent)


def can_write(agent: str, role: str, path: str) -> bool:
    rel = _rel(path)
    if rel is None:
        return False
    return _match(rel, WRITE.get(role, []), agent) and not _match(rel, WRITE_DENY_ALL, agent)


def check(agent: str, role: str, tool: str, args: dict) -> str | None:
    """Return a denial reason, or None if allowed."""
    if tool in ("Read", "NotebookRead"):
        p = args.get("file_path", "")
        return None if can_read(agent, role, p) else f"{role} '{agent}' may not read {p}"
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        p = args.get("file_path") or args.get("notebook_path", "")
        return None if can_write(agent, role, p) else f"{role} '{agent}' may not write {p} (see rules/common.md#files)"
    if tool in ("Glob", "Grep"):
        p = args.get("path")
        pat = args.get("pattern", "")
        if tool == "Glob" and os.path.isabs(pat) and _rel(pat.split("*")[0] or "/") is None:
            return "patterns must stay inside the repo"
        if not p:
            return None if READ.get(role) == ["**"] else "pass an explicit `path` you are allowed to read"
        pat = args.get("pattern", "") + args.get("glob", "")
        if ".." in pat or (tool == "Glob" and os.path.isabs(args.get("pattern", ""))
                           and _rel(args["pattern"].split("*")[0] or "/") is None):
            return "patterns must stay inside the repo (no '..' or outside absolute paths)"
        if os.path.isfile(_abs(p)):
            return None if can_read(agent, role, p) else f"{role} '{agent}' may not read {p}"
        return None if can_read_dir(agent, role, p) else f"{role} '{agent}' may not search {p}"
    return f"tool {tool} is not available"


def _abs(p: str) -> str:
    return p if os.path.isabs(p) else str(ROOT / p)


def make_hook(agent: str, role: str):
    async def hook(input_data, tool_use_id, context):
        reason = check(agent, role, input_data["tool_name"], input_data.get("tool_input") or {})
        if reason is None:
            return {}
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "permissionDecision": "deny",
                                       "permissionDecisionReason": reason}}
    return hook
