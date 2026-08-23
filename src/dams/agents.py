"""Agent runner — invokes Hermes profile agents with double-blind isolation."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROFILE_MAP = {
    "architect": "architect",
    "coder": "coder",
    "tester": "tester",
    "triage": "triage",
    "reviewer": "reviewer",
    "maintainer": "maintainer",
}


@dataclass
class AgentResult:
    role: str
    ok: bool
    output: str
    session_id: Optional[str] = None


def run_agent(role: str, prompt: str, workdir: Path, timeout: int = 900,
              extra_env_isolation: bool = True) -> AgentResult:
    """Run `hermes chat -q` under the given profile, in the given workdir."""
    profile = PROFILE_MAP.get(role)
    if profile is None:
        raise ValueError(f"unknown agent role: {role}")
    cmd = ["hermes", "--profile", profile, "chat", "-q", prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(workdir))
    except subprocess.TimeoutExpired:
        return AgentResult(role=role, ok=False, output="[TIMEOUT after %ds]" % timeout)
    combined = (r.stdout or "") + (r.stderr or "")
    sid = None
    for line in combined.splitlines():
        if "Session:" in line and "_" in line:
            sid = line.split("Session:")[-1].strip()
            break
    return AgentResult(role=role, ok=(r.returncode == 0), output=combined.strip(),
                       session_id=sid)


def extract_json(text: str) -> Optional[dict]:
    """Best-effort extraction of the first JSON object in an agent response."""
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = None
    return None
