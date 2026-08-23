"""Append-only event bus — the dashboard's source of truth for audit/history.

Every orchestrator action appends a JSON line to <root>/.dams/events.jsonl:
    {"ts": iso8601, "source": "phase1|phase2|controller|dashboard",
     "role": "coder|tester|...", "event": "gate_failed",
     "severity": "info|warn|error|sanitized", "data": {...}}
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

_lock = threading.Lock()


def _events_path(root: Path) -> Path:
    d = Path(root) / ".dams"
    d.mkdir(parents=True, exist_ok=True)
    return d / "events.jsonl"


def emit(root: Path, event: str, source: str = "orchestrator",
         role: str = "", severity: str = "info", **data) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "role": role,
        "event": event,
        "severity": severity,
        "data": data,
    }
    with _lock:
        with open(_events_path(Path(root)), "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")


def read_events(root: Path, limit: int = 500,
                role: str | None = None, severity: str | None = None,
                source: str | None = None) -> list[dict]:
    path = _events_path(Path(root))
    if not path.exists():
        return []
    out: list[dict] = []
    with _lock:
        with open(path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if role and rec.get("role") != role:
                    continue
                if severity and rec.get("severity") != severity:
                    continue
                if source and rec.get("source") != source:
                    continue
                out.append(rec)
    return out[-limit:]


def tail(root: Path, n: int = 20) -> list[dict]:
    return read_events(Path(root), limit=n)


class EventBusLog:
    """Drop-in `log` callable for orchestrators that mirrors output to the bus."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def __call__(self, message: str) -> None:
        print(message, flush=True)
        # Parse "[P1/U3] pre-gate 'lint' failed" style lines into events
        severity = "info"
        event = "log"
        low = message.lower()
        if "fail" in low or "tripped" in low or "fatal" in low:
            severity = "error"
            event = "failure"
        elif "arbitration" in low:
            event = "arbitration"
            severity = "warn"
        elif "pass" in low or "green" in low or "skip" in low or "complete" in low:
            event = "success"
        role = ""
        for r in ("architect", "coder", "tester", "triage", "reviewer",
                  "maintainer"):
            if f"/{r}" in message.lower():
                role = r
                break
        emit(self.root, event=event, source="orchestrator", role=role,
             severity=severity, message=message)
