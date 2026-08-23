#!/usr/bin/env python3
"""E2E driver: double-blind coder/tester round for demo_project Unit 1."""
import sys
from pathlib import Path

sys.path.insert(0, "/home/megh/DAMS/src")
from dams.agents import run_agent  # noqa: E402

root = Path("/home/megh/DAMS/demo_project")
c = run_agent("coder",
              "Implement Unit 1 per docs/specs/spec.md and agent_manifest.json. "
              "Create src/calc.py with add/sub/mul/div; div raises ZeroDivisionError "
              "when b == 0. Do not read tests/.",
              root, timeout=900)
t = run_agent("tester",
              "Write black-box pytest tests in tests/ for Unit 1 (add, sub, mul, div; "
              "div raises ZeroDivisionError) based ONLY on docs/specs/spec.md — do not "
              "read src/. Ensure 'python3 -m pytest tests -q' works from the project root.",
              root, timeout=900)
print(f"RESULT coder_ok={c.ok} tester_ok={t.ok}")
