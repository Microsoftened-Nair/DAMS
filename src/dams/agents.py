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
    """Run `hermes chat -q` under the given profile, in the given workdir.

    Root discipline: the absolute project workdir is prepended to every prompt
    and agents are instructed to operate ONLY inside it, so they never resolve
    paths to some parent repo root.
    """
    profile = PROFILE_MAP.get(role)
    if profile is None:
        raise ValueError(f"unknown agent role: {role}")
    root = Path(workdir).resolve()
    scoped_prompt = (
        f"PROJECT ROOT: {root}\n"
        f"You MUST operate exclusively inside this directory — every file you read "
        f"or write must be under it, and relative paths in specs/manifests resolve "
        f"from here. Do NOT touch parent directories.\n\n{prompt}"
    )
    scoped_prompt = apply_ponytail(scoped_prompt, role)
    cmd = ["hermes", "--profile", profile, "chat", "-q", scoped_prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(root))
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


# Prompt-layer ruleset injected into coder/reviewer prompts (Ponytail).
# Source: github.com/DietrichGebert/ponytail (MIT). Kept here so the
# orchestrator enforces it even if profile SOUL.md files are regenerated.
PONYTAIL_LADDER = (
    "PONYTAIL RULES — lazy senior dev mode. Before writing code, stop at the "
    "first rung that holds: (1) YAGNI — does this need to exist? "
    "(2) already in this codebase? reuse it. (3) stdlib does it? use it. "
    "(4) native platform feature? use it. (5) installed dependency solves it? "
    "use it. (6) can it be one line? make it one. (7) only then: minimum code "
    "that works. No unrequested abstractions, no new dependencies, no "
    "boilerplate. Deletion over addition, boring over clever, fewest files. "
    "Never be lazy about: understanding the problem, input validation at "
    "trust boundaries, error handling preventing data loss, security, or "
    "anything the spec explicitly requires."
)


def apply_ponytail(prompt: str, role: str) -> str:
    """Append the ponytail ruleset for frugal roles (coder, reviewer)."""
    if role in ("coder", "reviewer"):
        return prompt + "\n\n" + PONYTAIL_LADDER
    return prompt
