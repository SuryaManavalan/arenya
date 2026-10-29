"""Local web dashboard: `uv run arenya dashboard` → http://localhost:8765

Read-only views of the game, plus three human actions (reply, post, pause/resume) that go through
engine.post_message / state.locked exactly like the CLI, so they're safe while the dispatcher runs.
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from . import channels, engine, state
from .config import LOGS_DIR, ROOT, roster, settings

HTML = Path(__file__).with_name("dashboard.html")
READABLE = ("library/", "world/", "books/", "plot/", "agents/", "rules/", "docs/")


def _frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            try:
                return yaml.safe_load(text[4:end]) or {}, text[end + 4:].lstrip("\n")
            except yaml.YAMLError:
                pass
    return {}, text


def _section(md: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def _jsonl(name: str, limit: int = 2000) -> list[dict]:
    p = LOGS_DIR / f"{name}.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def api_state() -> dict:
    with state.locked() as st:
        charges = {a: engine.charges_left(st, a) for a in roster()}
        snap = json.loads(json.dumps(st))
    agents = roster()
    cfg = settings()
    cast = {}
    for aid, entry in agents.items():
        folder = ROOT / "agents" / aid
        sheet = {}
        if (folder / "sheet.yaml").exists():
            try:
                sheet = yaml.safe_load((folder / "sheet.yaml").read_text()) or {}
            except yaml.YAMLError:
                sheet = {}
        mem = (folder / "MEMORY.md").read_text() if (folder / "MEMORY.md").exists() else ""
        ident = (folder / "IDENTITY.md").read_text() if (folder / "IDENTITY.md").exists() else ""
        rc = cfg["roles"].get(entry["role"], {})
        cast[aid] = {
            **entry, "charges": charges.get(aid), "base_gear": rc.get("base_gear"), "peak_gear": rc.get("peak_gear"),
            "sheet": sheet, "now": _section(mem, "Who I am right now"), "wants": _section(mem, "What I want"),
            "memory_updated": (re.search(r"_Last updated: (.*?)_", mem) or [None, ""])[1],
            "identity_head": "\n".join(l for l in ident.splitlines()[1:8] if l.strip()),
            "location": (snap.get("locations") or {}).get(aid),
        }
    usage = _jsonl("usage")
    cost = sum(r.get("cost_usd") or 0 for r in usage)
    return {"state": snap, "cast": cast, "charges": charges, "cost_total": round(cost, 3),
            "turns_total": len(usage), "gears": cfg["gears"],
            "channels": channels.all_channel_names(agents)}


def api_messages(book: int | None) -> list[dict]:
    st = state.load()
    books = [book] if book else list(range(1, st["book"] + 1))
    return channels.all_messages(st, books)


def api_library() -> dict:
    groups: dict[str, list[dict]] = {}
    for top in ("library", "world", "plot", "books"):
        base = ROOT / top
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.md")):
            rel = p.relative_to(ROOT).as_posix()
            fm, _ = _frontmatter(p.read_text())
            groups.setdefault(str(Path(rel).parent), []).append({
                "path": rel, "name": fm.get("name") or fm.get("title") or p.stem,
                "type": fm.get("type"), "visibility": fm.get("visibility")
                or ("restricted" if "/restricted/" in rel else None),
                "status": fm.get("status")})
    return groups


def api_file(path: str) -> dict:
    p = (ROOT / path).resolve()
    if not str(p).startswith(str(ROOT)) or not any(path.startswith(r) for r in READABLE) or not p.is_file():
        return {"error": "not readable"}
    text = p.read_text()
    if p.suffix in (".yaml", ".yml"):
        return {"path": path, "frontmatter": {}, "body": f"```yaml\n{text}\n```"}
    fm, body = _frontmatter(text)
    return {"path": path, "frontmatter": fm, "body": body}


def api_places() -> dict:
    p = ROOT / "library/places.yaml"
    return (yaml.safe_load(p.read_text()) or {}).get("places", {}) if p.exists() else {}


def api_activity() -> dict:
    return {"usage": _jsonl("usage", 1500), "errors": _jsonl("errors", 100),
            "gears": _jsonl("gears", 300), "rolls": _jsonl("rolls", 500)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, obj, code=200, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self._send(HTML.read_bytes(), ctype="text/html; charset=utf-8")
            if u.path == "/api/state":
                return self._send(api_state())
            if u.path == "/api/messages":
                return self._send(api_messages(int(q["book"]) if q.get("book") else None))
            if u.path == "/api/library":
                return self._send(api_library())
            if u.path == "/api/file":
                return self._send(api_file(q.get("path", "")))
            if u.path == "/api/places":
                return self._send(api_places())
            if u.path == "/api/activity":
                return self._send(api_activity())
            self._send({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._send({"error": repr(e)}, 500)

    def do_POST(self):
        u = urlparse(self.path)
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        try:
            if u.path == "/api/reply":
                m = engine.post_message("human", "human", "answer", data["text"], reply_to=int(data["id"]))
                return self._send({"ok": True, "id": m["id"]})
            if u.path == "/api/say":
                m = engine.post_message("human", data["channel"], data.get("type", "note"), data["text"],
                                        to=data.get("to") or [], awaits=data.get("awaits") or [])
                return self._send({"ok": True, "id": m["id"]})
            if u.path in ("/api/pause", "/api/resume"):
                with state.locked() as st:
                    st["paused"] = u.path.endswith("pause")
                    st["pause_reason"] = "paused from dashboard" if st["paused"] else None
                    if not st["paused"]:
                        st["idle_wakes"] = 0
                return self._send({"ok": True})
            self._send({"error": "not found"}, 404)
        except engine.PostError as e:
            self._send({"error": str(e)}, 400)
        except Exception as e:  # noqa: BLE001
            self._send({"error": repr(e)}, 500)


def serve(port: int = 8765, host: str = "127.0.0.1") -> None:
    print(f"Arenya dashboard → http://localhost:{port}  (Ctrl-C to stop)", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
