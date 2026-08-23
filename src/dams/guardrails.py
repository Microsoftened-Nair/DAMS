"""Deterministic safety guardrails.

- Test assertion monotonicity gate
- Diff size ceiling
- Iteration circuit breaker (3-attempt rule)
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

MAX_DIFF_LINES = 500
MAX_ITERATIONS = 3


@dataclass
class GuardrailViolation(Exception):
    reason: str


def count_assertions(test_dir: Path) -> int:
    """Count collected tests deterministically via pytest --collect-only -q."""
    r = subprocess.run(
        ["python3", "-m", "pytest", str(test_dir), "--collect-only", "-q"],
        capture_output=True, text=True, cwd=str(test_dir.parent if test_dir.name != "tests" else test_dir.parent),
    )
    # pytest -q collect output ends with "N tests collected" or a count line
    for line in reversed(r.stdout.strip().splitlines()):
        line = line.strip()
        if line.endswith("tests collected") or (line.isdigit()):
            try:
                return int(line.split()[0])
            except ValueError:
                continue
    return 0


def check_monotonicity(before: int, after: int) -> None:
    """Reject if any test was deleted/skipped: count must never decrease."""
    if after < before:
        raise GuardrailViolation(
            f"Test assertion monotonicity violated: {before} -> {after} tests "
            f"({before - after} deleted). PR blocked."
        )


def diff_stats(repo: Path, base: str = "main", head: str = "HEAD") -> tuple:
    r = subprocess.run(["git", "-C", str(repo), "diff", "--shortstat", f"{base}...{head}"],
                       capture_output=True, text=True)
    out = r.stdout.strip()
    files = lines = 0
    import re as _re
    m = _re.search(r"(\d+) files? changed", out)
    if m:
        files = int(m.group(1))
    m = _re.search(r"(\d+) insertions?", out)
    ins = int(m.group(1)) if m else 0
    m = _re.search(r"(\d+) deletions?", out)
    dele = int(m.group(1)) if m else 0
    return files, ins + dele


def check_diff_ceiling(repo: Path, base: str = "main") -> None:
    _, changed = diff_stats(repo, base=base)
    if changed > MAX_DIFF_LINES:
        raise GuardrailViolation(
            f"Diff size ceiling exceeded: {changed} > {MAX_DIFF_LINES} lines. "
            "Blocked from autonomous merge; assign @human-review."
        )


@dataclass
class CircuitBreaker:
    """3-attempt circuit breaker between two parties before arbitration."""
    max_attempts: int = MAX_ITERATIONS
    attempts: int = 0
    history: list = field(default_factory=list)

    def record_failure(self, note: str) -> None:
        self.attempts += 1
        self.history.append(note)

    def tripped(self) -> bool:
        return self.attempts >= self.max_attempts
