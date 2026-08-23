"""Phase 1: Greenfield Build — synchronous orchestrator.

Loop per spec:
  1. Architect ingests goal -> docs/specs/spec.md + agent_manifest.json + task units
  2. Contract broadcast to Coder + Tester (double-blind)
  3. Deterministic pre-gate: lint/typecheck from manifest
  4. test_unit execution; failures pass through the AST sanitizer
  5. Visual QA gate for web/desktop
  6. 3-attempt circuit breaker -> Architect arbitration
  7. Tag v1.0.0-baseline when all units pass
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import time
from pathlib import Path

from .agents import extract_json, run_agent
from .guardrails import CircuitBreaker
from .manifest import Manifest, ManifestError, load as load_manifest
from .sanitizer import sanitize

UNIT_TIMEOUTS = {"coder": 1200, "tester": 1200}


class Phase1Orchestrator:
    def __init__(self, root: Path, log=print):
        self.root = Path(root).resolve()
        self.log = log

    # -- helpers ---------------------------------------------------------------
    def _run_manifest_cmd(self, manifest: Manifest, name: str) -> tuple:
        cmd = manifest.cmd(name)
        if not cmd:
            return True, "", ""
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           cwd=str(self.root), timeout=600)
        return r.returncode == 0, r.stdout, r.stderr

    def _spec_units(self, manifest: Manifest) -> list:
        """Read ordered atomic units from docs/specs/spec.md (## Unit N: ...)."""
        spec = self.root / manifest.contract("specs_dir") / "spec.md"
        if not spec.exists():
            return []
        text = spec.read_text()
        return re.findall(r"^#{2,3}\s*Unit\s+(\d+)\s*:?\s*(.+)$", text, re.M)

    # -- main loop ---------------------------------------------------------------
    def run(self, goal: str) -> bool:
        self.log(f"[P1] Goal ingestion: {goal[:100]}...")

        # Step 1: Architecture
        run_agent("architect",
                  "Project request:\n" + goal +
                  "\n\nProduce docs/specs/spec.md with sections '## Unit N: <name>' "
                  "(ordered atomic implementation specs with explicit I/O JSON schemas), "
                  "and write agent_manifest.json at the repo root per the schema. "
                  "Do not write source or test code.",
                  workdir=self.root, timeout=1800)

        try:
            manifest = load_manifest(self.root)
        except ManifestError as e:
            self.log(f"[P1] FATAL: invalid manifest: {e}")
            return False
        self.log(f"[P1] Manifest OK: {manifest.project_name} ({manifest.ui_type})")

        units = self._spec_units(manifest)
        if not units:
            self.log("[P1] FATAL: Architect produced no parseable Unit headings in spec.md")
            return False
        self.log(f"[P1] {len(units)} unit(s): {[u[0] for u in units]}")

        all_pass = True
        for unit_no, unit_title in units:
            ok = self._build_unit(manifest, int(unit_no), unit_title)
            all_pass = all_pass and ok

        if all_pass:
            subprocess.run(["git", "tag", "-f", "v1.0.0-baseline"], cwd=str(self.root))
            self.log("[P1] All units green. Tagged v1.0.0-baseline. Phase 1 complete.")
        else:
            self.log("[P1] Some units failed after arbitration; see logs.")
        return all_pass

    # -- per-unit loop -----------------------------------------------------------
    def _build_unit(self, manifest: Manifest, unit_no: int, title: str) -> bool:
        breaker = CircuitBreaker()
        contract = (
            f"Implement specification Unit {unit_no}: {title}\n"
            f"Read docs/specs/spec.md and agent_manifest.json for full contract details.\n"
            f"Source dir: {manifest.contract('source_dir')}. Do NOT read tests/."
        )
        test_contract = (
            f"Write black-box tests for Unit {unit_no}: {title}\n"
            f"Read docs/specs/spec.md and agent_manifest.json for full contract details.\n"
            f"Test dir: {manifest.contract('test_dir')}. You are BLIND to src/."
        )

        while True:
            # Double-blind parallel dispatch (sequential subprocesses; contract broadcast)
            coder_res = run_agent("coder", contract, self.root,
                                  timeout=UNIT_TIMEOUTS["coder"])
            tester_res = run_agent("tester", test_contract, self.root,
                                   timeout=UNIT_TIMEOUTS["tester"])
            self.log(f"[P1/U{unit_no}] coder ok={coder_res.ok} tester ok={tester_res.ok}")

            # Deterministic pre-gate
            for gate in ("lint", "typecheck"):
                ok, out, err = self._run_manifest_cmd(manifest, gate)
                if not ok:
                    feedback = sanitize(out + err)
                    self.log(f"[P1/U{unit_no}] pre-gate '{gate}' failed -> back to Coder")
                    breaker.record_failure(f"{gate} failed")
                    if breaker.tripped():
                        return self._arbitrate(unit_no, title, feedback)
                    contract += f"\n\nSanitized diagnostics from previous attempt:\n{feedback}"
                    continue_outer = True
                    break
            else:
                continue_outer = False
            if continue_outer:
                continue

            # Test gate
            ok, out, err = self._run_manifest_cmd(manifest, "test_unit")
            if ok:
                self.log(f"[P1/U{unit_no}] tests PASS")
                if manifest.needs_visual_qa():
                    self._visual_qa(manifest, unit_no)
                return True

            sanitized = sanitize(out + err)
            self.log(f"[P1/U{unit_no}] tests FAIL ({len(sanitized)} chars sanitized diag)")
            breaker.record_failure("unit tests failed")
            if breaker.tripped():
                return self._arbitrate(unit_no, title, sanitized)
            contract += f"\n\nSanitized failure diagnostics (tests redacted):\n{sanitized}"

    # -- visual QA ------------------------------------------------------------
    def _visual_qa(self, manifest: Manifest, unit_no: int) -> bool:
        port = random.randint(20000, 45000)
        server_cmd = manifest.cmd("dev_server") or ""
        env_cmd = f"{manifest.contract('port_variable')}={port} {server_cmd}"
        proc = subprocess.Popen(env_cmd, shell=True, cwd=str(self.root),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(4)  # allow boot
            res = run_agent(
                "tester",
                f"VISUAL QA Unit {unit_no}: dev server on http://127.0.0.1:{port}. "
                "Use Playwright bounding boxes (getBoundingClientRect) to detect DOM "
                "collisions and take screenshots at 1920x1080 and 375x812. Report "
                "clipping/overlap/balance issues as JSON: {\"pass\": bool, \"issues\": []}.",
                self.root, timeout=900)
            verdict = extract_json(res.output) or {}
            passed = bool(verdict.get("pass", res.ok))
            self.log(f"[P1/U{unit_no}] visual QA pass={passed}")
            return passed
        finally:
            proc.terminate()

    # -- arbitration ----------------------------------------------------------
    def _arbitrate(self, unit_no: int, title: str, diagnostics: str) -> bool:
        self.log(f"[P1/U{unit_no}] circuit breaker tripped -> Architect arbitration")
        res = run_agent(
            "architect",
            f"ARBITRATION for Unit {unit_no}: {title}\n"
            f"Coding stalled after 3 failed attempts. Sanitized diagnostics:\n"
            f"{diagnostics[:4000]}\n\nEvaluate the ambiguity, issue a binding ruling, "
            "and update docs/specs/spec.md accordingly.",
            self.root, timeout=1200)
        with open(self.root / "docs" / "specs" / "arbitration.log", "a") as f:
            f.write(f"\n=== Arbitration U{unit_no}: {title} ===\n{res.output[-2000:]}\n")
        # One post-arbitration retry cycle is allowed before giving up.
        m = load_manifest(self.root)
        contract = (f"Implement specification Unit {unit_no}: {title}\n"
                    f"The Architect has issued a binding clarification — re-read "
                    f"docs/specs/spec.md and implement accordingly.")
        run_agent("coder", contract, self.root, timeout=UNIT_TIMEOUTS["coder"])
        ok, _, _ = self._run_manifest_cmd(m, "test_unit")
        self.log(f"[P1/U{unit_no}] post-arbitration tests {'PASS' if ok else 'FAIL'}")
        return ok
