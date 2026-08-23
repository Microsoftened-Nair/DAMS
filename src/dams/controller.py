"""Phase 2 service controller — start / stop / status a long-running pipeline.

State lives under <root>/.dams/:
    phase2.pid      PID of the running pipeline process
    phase2.log      live log output
    phase2.stop     sentinel file — graceful stop request

Graceful semantics: 'stop' sets the sentinel AND signals the process; the
pipeline finishes its current issue lifecycle (or aborts the current agent
call if you use --force), then exits cleanly.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def _state_dir(root: Path) -> Path:
    d = root / ".dams"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_pid(root: Path) -> int | None:
    f = _state_dir(root) / "phase2.pid"
    if not f.exists():
        return None
    try:
        return int(f.read_text().strip())
    except ValueError:
        return None


def is_running(root: Path) -> bool:
    pid = _read_pid(root)
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        ( _state_dir(root) / "phase2.pid").unlink(missing_ok=True)
        return False


def start(root: Path, issues: int | None = None, cycles: int | None = None,
          dry_run: bool = False) -> bool:
    root = root.resolve()
    if is_running(root):
        print(f"[serve] Phase 2 already running for {root} "
              f"(PID {_read_pid(root)}). Use 'stop' first.")
        return False
    state = _state_dir(root)
    (state / "phase2.stop").unlink(missing_ok=True)

    cmd = [sys.executable, str(Path(__file__).resolve().parent / "phase2_daemon.py"),
           "--root", str(root)]
    if issues:
        cmd += ["--issues", str(issues)]
    if cycles:
        cmd += ["--cycles", str(cycles)]
    if dry_run:
        cmd.append("--dry-run")

    logf = open(state / "phase2.log", "a")
    proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, start_new_session=True)
    (state / "phase2.pid").write_text(str(proc.pid))
    # give it a moment to boot
    time.sleep(1.5)
    alive = proc.poll() is None
    print(f"[serve] {'started' if alive else 'FAILED TO START'} — "
          f"PID {proc.pid}, log: {state / 'phase2.log'}")
    return alive


def stop(root: Path, force: bool = False) -> bool:
    root = root.resolve()
    if not is_running(root):
        print("[serve] not running.")
        return False
    pid = _read_pid(root)
    state = _state_dir(root)
    if force:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
        print(f"[serve] force-killed PID {pid}.")
    else:
        (state / "phase2.stop").write_text("stop")
        os.kill(pid, signal.SIGTERM)
        print(f"[serve] stop requested — finishing current issue lifecycle, "
              f"then exiting. Watch {state / 'phase2.log'}")
    (state / "phase2.pid").unlink(missing_ok=True)
    return True


def status(root: Path) -> dict:
    root = root.resolve()
    running = is_running(root)
    info = {
        "running": running,
        "pid": _read_pid(root) if running else None,
        "log": str(_state_dir(root) / "phase2.log"),
        "stop_requested": (_state_dir(root) / "phase2.stop").exists(),
    }
    tail = ""
    if running or info["stop_requested"]:
        logf = Path(info["log"])
        if logf.exists():
            lines = logf.read_text().splitlines()
            tail = "\n".join(lines[-5:])
    return {**info, "recent_log": tail}
