#!/usr/bin/env python3
"""DAMS CLI — dual-phase autonomous multi-agent SDLC orchestrator."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from dams.phase1 import Phase1Orchestrator          # noqa: E402
from dams.phase2 import Phase2Pipeline              # noqa: E402


def main():
    ap = argparse.ArgumentParser(prog="dams")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("phase1", help="Greenfield build")
    p1.add_argument("--root", default=".")
    p1.add_argument("goal")

    p2 = sub.add_parser("phase2", help="Maintenance pipeline (one cycle)")
    p2.add_argument("--root", default=".")
    p2.add_argument("--dry-run", action="store_true")
    p2.add_argument("--cycles", type=int, default=1)

    sub.add_parser("smoke", help="Run framework self-test (no LLM calls)")

    args = ap.parse_args()
    root = Path(args.root if hasattr(args, "root") else ".").resolve()

    if args.cmd == "phase1":
        ok = Phase1Orchestrator(root).run(args.goal)
        sys.exit(0 if ok else 1)
    elif args.cmd == "phase2":
        pipe = Phase2Pipeline(root, dry_run=args.dry_run)
        for i in range(args.cycles):
            print(f"=== Phase 2 cycle {i+1}/{args.cycles} ===")
            res = pipe.run_once()
            print(res)
    else:
        from dams.smoke_test import run as smoke
        smoke(root)


if __name__ == "__main__":
    main()
