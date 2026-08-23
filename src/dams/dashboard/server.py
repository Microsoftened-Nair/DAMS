"""Dashboard backend — FastAPI app with token auth, REST + WebSocket.

Run:  python3 dams.py --root <project> serve-ui [--port 8420]
Auth: Bearer DAMS_CONTROL_TOKEN from <root>/.dams/control_token
      (auto-generated on first start).
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ..events import emit, read_events
from ..manifest import ManifestError, load as load_manifest
from .. import controller

app = FastAPI(title="DAMS Command Center", version="0.1.0")
_root: Path = Path(".").resolve()
_ws_clients: set[WebSocket] = set()


# ---------------------------------------------------------------- auth
def _token_file() -> Path:
    d = _root / ".dams"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "control_token"
    if not f.exists():
        f.write_text(secrets.token_urlsafe(32))
        os.chmod(f, 0o600)
    return f


def require_auth(authorization: str = Header(default="")) -> None:
    expected = "Bearer " + _token_file().read_text().strip()
    if authorization != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


# ---------------------------------------------------------------- helpers
def _state_dir() -> Path:
    return _root / ".dams"


def _fleet_status() -> list[dict]:
    """Scan live hermes profile processes + recent events for the grid."""
    roles = ["architect", "coder", "tester", "triage", "reviewer", "maintainer"]
    try:
        out = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True,
                             text=True, timeout=10).stdout
    except Exception:
        out = ""
    cards = []
    for role in roles:
        live = [l for l in out.splitlines()
                if f"--profile {role}" in l and "grep" not in l]
        running = bool(live)
        pids = [l.strip().split()[0] for l in live]
        evts = read_events(_root, limit=200, role=role)
        last = evts[-1] if evts else None
        status = ("RUNNING" if running else
                  (last["event"].upper() if last else "IDLE"))
        cards.append({
            "role": role,
            "model": "stealth/ox-alpha",
            "provider": "openrouter",
            "status": status,
            "pids": pids,
            "last_event": last,
            "domain": {
                "architect": "docs/specs/*, agent_manifest.json",
                "coder": "src/* (worktree state when fixing)",
                "tester": "tests/*",
                "triage": "issues, ephemeral workspace",
                "reviewer": "read-only diff",
                "maintainer": "main branch merges",
            }[role],
        })
    return cards


def _pipeline_state() -> dict:
    st = controller.status(_root)
    pause_flag = _state_dir() / "pause"
    return {
        **st,
        "paused": pause_flag.exists() or st.get("stop_requested", False),
        "project": _root.name,
    }


async def _broadcast(message: dict) -> None:
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


async def _telemetry_loop():
    """Push fleet/pipeline/events snapshots to WS clients every 5s."""
    while True:
        if _ws_clients:
            await _broadcast({
                "type": "telemetry",
                "pipeline": _pipeline_state(),
                "fleet": _fleet_status(),
                "events": read_events(_root, limit=50),
                "ts": time.time(),
            })
        await asyncio.sleep(5)


@app.on_event("startup")
async def startup():
    asyncio.create_task(_telemetry_loop())


# ---------------------------------------------------------------- REST
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/state", dependencies=[Depends(require_auth)])
def api_state():
    return {"pipeline": _pipeline_state(), "fleet": _fleet_status()}


@app.get("/api/events", dependencies=[Depends(require_auth)])
def api_events(limit: int = 200, role: str = "", severity: str = ""):
    return read_events(_root, limit=limit, role=role or None,
                       severity=severity or None)


@app.get("/api/manifest", dependencies=[Depends(require_auth)])
def api_manifest():
    try:
        m = load_manifest(_root)
        return {"valid": True, "manifest": json.loads(m.to_json())}
    except ManifestError as e:
        return {"valid": False, "error": str(e)}


@app.get("/api/spec", dependencies=[Depends(require_auth)])
def api_spec():
    spec = _root / "docs" / "specs" / "spec.md"
    return {"exists": spec.exists(),
            "content": spec.read_text() if spec.exists() else ""}


@app.post("/api/spec", dependencies=[Depends(require_auth)])
def api_spec_save(body: dict):
    content = body.get("content", "")
    ( _root / "docs" / "specs").mkdir(parents=True, exist_ok=True)
    (_root / "docs" / "specs" / "spec.md").write_text(content)
    emit(_root, "spec_edited", source="dashboard", severity="warn",
         chars=len(content))
    return {"saved": True, "chars": len(content)}


@app.get("/api/cleanroom", dependencies=[Depends(require_auth)])
def api_cleanroom():
    def tree(base: Path):
        if not base.exists():
            return []
        return sorted(str(p.relative_to(_root))
                      for p in base.rglob("*") if p.is_file())
    return {
        "src_files": tree(_root / "src"),
        "test_files": tree(_root / "tests"),
        "worktrees": tree(_root / ".worktrees"),
    }


@app.get("/api/file", dependencies=[Depends(require_auth)])
def api_file(path: str):
    target = (_root / path).resolve()
    if not str(target).startswith(str(_root)):
        raise HTTPException(400, "path escapes project root")
    if not target.is_file():
        raise HTTPException(404, "not found")
    try:
        return {"path": path, "content": target.read_text(errors="replace")[:100_000]}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/costs", dependencies=[Depends(require_auth)])
def api_costs():
    """Aggregate session_model_usage across the six profile DBs."""
    totals = []
    for role in ("architect", "coder", "tester", "triage", "reviewer",
                 "maintainer"):
        db = Path.home() / ".hermes" / "profiles" / role / "state.db"
        row = None
        if db.exists():
            import sqlite3
            try:
                conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
                cols = [c[1] for c in conn.execute(
                    "PRAGMA table_info(session_model_usage)")]
                if cols:
                    sel = ", ".join(c for c in cols if c not in ("id",))
                    # just sum numeric columns generically
                    num_cols = [c for c in cols if any(
                        k in c.lower() for k in
                        ("tokens", "input", "output", "cost", "calls"))]
                    if num_cols:
                        sums = ", ".join(
                            f"SUM({c}) AS {c}" for c in num_cols)
                        row = dict(zip(num_cols, conn.execute(
                            f"SELECT {sums} FROM session_model_usage"
                        ).fetchone()))
                conn.close()
            except Exception:
                pass
        totals.append({"role": role, "usage": row})
    return {"roles": totals}


# ---- controls -------------------------------------------------------------
@app.post("/api/control/{action}", dependencies=[Depends(require_auth)])
def api_control(action: str, body: dict | None = None):
    body = body or {}
    if action == "pause":
        (_state_dir() / "pause").write_text("pause between agent rounds")
        emit(_root, "pipeline_paused", source="dashboard", severity="warn")
        return {"action": action, "ok": True}
    if action == "resume":
        (_state_dir() / "pause").unlink(missing_ok=True)
        emit(_root, "pipeline_resumed", source="dashboard")
        return {"action": action, "ok": True}
    if action == "stop":
        ok = controller.stop(_root, force=bool(body.get("force")))
        emit(_root, "pipeline_stopped", source="dashboard", severity="warn",
             force=bool(body.get("force")))
        return {"action": action, "ok": ok}
    if action == "start_phase2":
        issues = int(body.get("issues") or 0) or None
        ok = controller.start(_root, issues=issues)
        emit(_root, "phase2_started", source="dashboard", issues=issues)
        return {"action": action, "ok": ok}
    if action == "force_arbitration":
        (_state_dir() / "force_arbitration").write_text("now")
        emit(_root, "arbitration_forced", source="dashboard", severity="warn")
        return {"action": action, "ok": True}
    if action == "reset_breaker":
        (_state_dir() / "breaker_reset").write_text("reset")
        emit(_root, "circuit_breaker_reset", source="dashboard",
             severity="warn")
        return {"action": action, "ok": True}
    if action == "override_merge":
        sig = body.get("signature", "")
        if len(sig) < 4:
            raise HTTPException(400, "operator signature required")
        audit = _state_dir() / "audit_overrides.log"
        with open(audit, "a") as f:
            f.write(json.dumps({"ts": time.time(), "action": "merge_override",
                                "signature": sig}) + "\n")
        emit(_root, "manual_merge_override", source="dashboard",
             severity="warn", signature=sig)
        return {"action": action, "ok": True}
    raise HTTPException(404, f"unknown control action '{action}'")


# ---------------------------------------------------------------- WS
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str = ""):
    if token != _token_file().read_text().strip():
        await websocket.close(code=4401)
        return
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            # keep alive; commands arrive over REST
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


@app.get("/", dependencies=[Depends(require_auth)])
def index():
    html = Path(__file__).parent / "static" / "index.html"
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html.read_text())


def run_server(root: Path, port: int = 8420):
    global _root
    _root = root.resolve()
    tok = _token_file()
    print(f"DAMS Command Center: http://127.0.0.1:{port}")
    print(f"Control token (also in {_token_file()}): {tok.read_text().strip()}")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
