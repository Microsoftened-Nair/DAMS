#!/usr/bin/env python3
"""Phase 2 daemon — runs the maintenance pipeline until bounded limit or stop.

Run via controller.start(); do not invoke directly unless debugging.
Handles SIGTERM as a graceful-stop request: finishes the current issue
lifecycle, then exits. Writes .dams/phase2.stop acknowledgement.
"""
from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dams.phase2 import Phase2Pipeline  # noqa: E402

_stop_requested = False


def _on_sigterm(signum, frame):
    global _stop_requested
    _stop_requested = True


signal.signal(signal.SIGTERM, _on_sigterm)


class StoppablePipeline(Phase2Pipeline):
    def _should_stop(self) -> bool:
        if _stop_requested:
            self.log("[P2] graceful stop: SIGTERM received")
            return True
        if (self.root / ".dams" / "phase2.stop").exists():
            self.log("[P2] graceful stop: stop file present")
            return True
        return False

    def run_until(self, max_issues):
        self._issues_completed = 0
        results = []
        pause_flag = self.root / ".dams" / "pause"
        while self._issues_completed < max_issues:
            while pause_flag.exists():
                self.log("[P2] PAUSED via dashboard — waiting...")
                time.sleep(3)
            if self._should_stop():
                self.log(f"[P2] stopped cleanly at {self._issues_completed}/{max_issues} issues.")
                break
            self.log(f"[P2] cycle {self._issues_completed + 1}/{max_issues}")
            res = self.run_once()
            results.append(res)
            if res.issue is None:
                break
        (self.root / ".dams" / "phase2.stop").unlink(missing_ok=True)
        self.log("[P2] daemon exit.")
        return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--issues", type=int)
    ap.add_argument("--cycles", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pipe = StoppablePipeline(Path(args.root), dry_run=args.dry_run)
    max_issues = args.issues or args.cycles or 1
    pipe.run_until(max_issues)


if __name__ == "__main__":
    main()
