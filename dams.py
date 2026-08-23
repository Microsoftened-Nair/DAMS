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
    ap.add_argument("--root", default=".", help="project root (global flag)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("phase1", help="Greenfield build")
    p1.add_argument("--root", default=None)
    p1.add_argument("goal")

    p2 = sub.add_parser("phase2", help="Maintenance pipeline")
    p2.add_argument("--root", default=None)
    p2.add_argument("--dry-run", action="store_true")
    p2.add_argument("--cycles", type=int, default=1)
    p2.add_argument("--issues", type=int, default=None,
                    help="bounded run: stop after N full issue lifecycles")

    sub.add_parser("smoke", help="Run framework self-test (no LLM calls)")

    ui = sub.add_parser("serve-ui", help="Launch the dashboard web UI")
    ui.add_argument("--port", type=int, default=8420)

    sv = sub.add_parser("serve", help="Phase 2 service: start/stop/status")
    sv.add_argument("--root", default=None)
    sv.add_argument("action", choices=["start", "stop", "status"])
    sv.add_argument("--force", action="store_true", help="stop: kill immediately")
    sv.add_argument("--issues", type=int, help="start: stop after N issue lifecycles")
    sv.add_argument("--cycles", type=int, help="start: run N cycles")
    sv.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()
    root = Path(getattr(args, "root", None) or ".").resolve()

    if args.cmd == "phase1":
        ok = Phase1Orchestrator(root).run(args.goal)
        sys.exit(0 if ok else 1)
    elif args.cmd == "phase2":
        pipe = Phase2Pipeline(root, dry_run=args.dry_run)
        if args.issues:
            for i, res in enumerate(pipe.run_until(args.issues), 1):
                print(f"issue {i}: {res}")
        else:
            for i in range(args.cycles):
                print(f"=== Phase 2 cycle {i+1}/{args.cycles} ===")
                res = pipe.run_once()
                print(res)
    elif args.cmd == "serve":
        from dams.controller import start, stop, status
        if args.action == "start":
            ok = start(root, issues=args.issues, cycles=args.cycles,
                       dry_run=args.dry_run)
            sys.exit(0 if ok else 1)
        elif args.action == "stop":
            sys.exit(0 if stop(root, force=args.force) else 1)
        else:
            st = status(root)
            print(f"running: {st['running']}  pid: {st['pid']}  "
                  f"stop_requested: {st['stop_requested']}")
            print(f"log: {st['log']}")
            if st["recent_log"]:
                print("--- recent ---")
                print(st["recent_log"])
    elif args.cmd == "serve-ui":
        from dams.dashboard.server import run_server
        run_server(root, port=args.port)
    elif args.cmd == "smoke":
        from dams.smoke_test import run as smoke
        smoke(root)


if __name__ == "__main__":
    main()
