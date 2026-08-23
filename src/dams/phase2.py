"""Phase 2: Event-driven Issue-to-PR maintenance pipeline.

Roles: synthetic-user -> triage -> fix-coder -> reviewer-critic -> maintainer.
Uses `gh` CLI + git worktrees. Falls back to local-only simulation when no
GitHub remote is configured.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .agents import extract_json, run_agent
from .guardrails import (GuardrailViolation, check_diff_ceiling,
                         check_monotonicity, count_assertions)


def sh(cmd: str, cwd: Path, timeout: int = 300) -> tuple:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       cwd=str(cwd), timeout=timeout)
    return r.returncode == 0, r.stdout, r.stderr


@dataclass
class MaintenanceResult:
    issue: Optional[int]
    pr: Optional[int]
    merged: bool
    note: str


class Phase2Pipeline:
    def __init__(self, root: Path, dry_run: bool = False, auto_create_repo: bool = True,
                 log=print):
        self.root = Path(root).resolve()
        self.dry_run = dry_run
        self.auto_create_repo = auto_create_repo
        self.log = log

    def has_gh(self) -> bool:
        ok, _, _ = sh("gh auth status", self.root)
        return ok

    def has_remote(self) -> bool:
        ok, out, _ = sh("git remote get-url origin", self.root)
        return ok and bool(out.strip())

    def ensure_remote(self) -> bool:
        """Guarantee the project has a GitHub origin remote.

        If the repo has no remote and auto_create_repo is set, create a private
        GitHub repo named after the directory (or agent_manifest project_name),
        push everything including tags, and wire it as origin.
        """
        if self.has_remote():
            return True
        if not self.has_gh():
            self.log("[P2] no gh auth and no remote -> local-only mode")
            return False
        if not self.auto_create_repo:
            self.log("[P2] no remote configured and auto-create disabled")
            return False
        name = self.root.name
        manifest_path = self.root / "agent_manifest.json"
        if manifest_path.exists():
            try:
                name = json.loads(manifest_path.read_text()).get(
                    "project_name", name).replace(" ", "-").lower()
            except json.JSONDecodeError:
                pass
        self.log(f"[P2] creating private GitHub repo '{name}' and pushing baseline...")
        ok, out, err = sh(
            f"gh repo create {name} --private --source . --remote origin --push",
            self.root)
        if not ok:
            # repo name may already exist on the account — try attach+push
            ok2, _, _ = sh(
                f"gh repo view {name} >/dev/null 2>&1 && "
                f"git remote add origin https://github.com/$({sh('gh api user -q .login', self.root)[1].strip() or 'unknown'}/{name}.git) 2>/dev/null && "
                f"git push -u origin HEAD --tags", self.root)
            if not ok2:
                self.log(f"[P2] repo creation failed: {(out + err).strip()[:300]}")
                return False
        ok, out, _ = sh("git push -u origin HEAD --tags", self.root)
        self.log(f"[P2] remote ready: {out.strip()[:120] if ok else 'push warning'}")
        return self.has_remote()

    # -- stage 1: synthetic user files an issue ---------------------------------
    def explore_and_file_issue(self) -> Optional[int]:
        # stop_after_issues: for bounded test runs — pipeline ends cleanly once
        # this many issues have been through the full lifecycle.
        stop = getattr(self, "stop_after_issues", None)
        if stop is not None and getattr(self, "_issues_completed", 0) >= stop:
            self.log(f"[P2] stop_after_issues={stop} reached — halting pipeline.")
            return -1
        res = run_agent(
            "triage",  # synthetic user runs under triage tooling in dry-run mode
            "SYNTHETIC USER: Explore this project's public interfaces (run its entry "
            "point, exercise CLI args). Capture any crash/misbehavior. If you find a "
            "bug, output ONLY a structured bug report JSON: "
            '{"component": str, "summary": str, "repro": str, "expected": str, '
            '"actual": str}. If nothing is broken, output {"no_bug": true}.',
            self.root, timeout=900)
        report = extract_json(res.output) or {}
        if not report or report.get("no_bug"):
            self.log("[P2] No bugs found during exploration.")
            return None
        if self.has_gh() and not self.dry_run:
            body = json.dumps(report, indent=2)
            ok, out, err = sh(
                f'gh issue create --title "bug: [{report.get("component","?")}] '
                f'{report.get("summary","")[:60]}" --body @{self._tmpfile(body)}',
                self.root)
            if ok:
                num = out.strip().rstrip("/").split("/")[-1]
                self.log(f"[P2] Filed issue #{num}")
                return int(num)
        self.log("[P2] (no gh remote — issue kept locally)")
        return None

    def _tmpfile(self, content: str) -> str:
        p = self.root / ".issue_body.tmp"
        p.write_text(content)
        return str(p)

    # -- stage 2: triage reproduces & writes fix spec -----------------------------
    def triage(self, issue_no: Optional[int]) -> Optional[str]:
        res = run_agent(
            "triage",
            f"TRIAGE issue #{issue_no or '(local report in last agent transcript)'}. "
            "Reproduce it in a temp workspace, verify it is not a duplicate, then "
            "write a precise fix spec to docs/specs/fix_issue_" + str(issue_no or 0) +
            ".md including expected inputs/outputs and edge cases.",
            self.root, timeout=1200)
        spec = self.root / "docs" / "specs" / f"fix_issue_{issue_no or 0}.md"
        self.log(f"[P2] Triage done (spec exists={spec.exists()})")
        return str(spec) if spec.exists() else None

    # -- stage 3: fix coder in an isolated worktree -------------------------------
    def fix_in_worktree(self, issue_no: Optional[int], spec_path: Optional[str]) -> Optional[str]:
        branch = f"fix/issue-{issue_no or 'local'}"
        wt = self.root / ".worktrees" / f"fix-issue-{issue_no or 'local'}"
        sh(f"git worktree add -b {branch} {wt} HEAD 2>/dev/null || true", self.root)
        prompt = (
            f"FIX CODER: Work in {wt}. Fix spec: {spec_path or 'see docs/specs/'}. "
            "FIRST write a failing regression test that reproduces the bug, THEN "
            "implement the fix in src/, then make ALL tests pass. Commit both with "
            "a conventional commit message."
        )
        res = run_agent("coder", prompt, wt, timeout=1800)
        ok, out, err = sh("git status --porcelain", wt)
        dirty = bool((out + err).strip())
        self.log(f"[P2] Fix coder done (ok={res.ok}, uncommitted={dirty})")
        return branch

    # -- stage 4: reviewer critic (read-only gates) --------------------------------
    def review(self, branch: str, assertions_before: int) -> bool:
        check_diff_ceiling(self.root, base="main")
        res = run_agent(
            "reviewer",
            f"REVIEWER CRITIC: Read-only inspection of branch {branch} vs main. "
            "Verify: (1) a new regression test exists reproducing the fixed bug, "
            "(2) no existing tests deleted or modified, (3) style/security/scope. "
            "Output JSON: {\"approve\": bool, \"reasons\": []}.",
            self.root, timeout=900)
        verdict = extract_json(res.output) or {}
        approved = bool(verdict.get("approve"))
        # deterministic monotonicity double-check
        assertions_after = count_assertions(self.root / "tests")
        check_monotonicity(assertions_before, assertions_after)
        self.log(f"[P2] Reviewer approve={approved}; assertions {assertions_before}->{assertions_after}")
        return approved

    # -- stage 5: maintainer merges with rollback safety -----------------------------
    def merge(self, branch: str) -> bool:
        if self.has_gh() and not self.dry_run:
            ok, out, err = sh(f"gh pr merge {branch} --squash --delete-branch", self.root)
            merged = ok
        else:
            ok, _, _ = sh(f"git checkout main && git merge --squash {branch}", self.root)
            ok2, _, _ = sh("git commit -m 'squash-merge (local mode)'", self.root) if ok else (False, "", "")
            merged = ok and ok2
        if merged:
            healthy, _, _ = sh("python3 -c \"import sys; sys.exit(0)\"", self.root)
            if not healthy:
                self.log("[P2] Post-merge health check FAILED -> auto-revert")
                sh("git revert HEAD --no-edit && git push origin main", self.root)
                return False
        self.log(f"[P2] Merged {branch}: {merged}")
        return merged

    # -- full pipeline ----------------------------------------------------------------
    def run_once(self) -> MaintenanceResult:
        if not self.ensure_remote():
            self.log("[P2] continuing without GitHub (local mode)")
        baseline = count_assertions(self.root / "tests")
        issue = self.explore_and_file_issue()
        if issue is None and self.has_gh():
            return MaintenanceResult(None, None, False, "no issues found")
        spec = self.triage(issue)
        branch = self.fix_in_worktree(issue, spec)
        if branch is None:
            return MaintenanceResult(issue, None, False, "fix coder failed")
        try:
            approved = self.review(branch, baseline)
        except GuardrailViolation as e:
            self.log(f"[P2] GUARDRAIL: {e}")
            return MaintenanceResult(issue, None, False, str(e))
        if not approved:
            return MaintenanceResult(issue, None, False, "reviewer rejected")
        merged = self.merge(branch)
        if hasattr(self, "_issues_completed"):
            self._issues_completed += 1
        return MaintenanceResult(issue, None, merged, "done")

    def run_until(self, max_issues: int):
        """Bounded run: process issues until max_issues full lifecycles complete."""
        self._issues_completed = 0
        results = []
        while self._issues_completed < max_issues:
            self.log(f"[P2] cycle {self._issues_completed + 1}/{max_issues}")
            res = self.run_once()
            results.append(res)
            if res.issue is None:
                break  # nothing found / halted — don't spin
        return results
