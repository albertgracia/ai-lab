"""FASE 29.0 — Gateway Process Guard.

Singleton enforcement, port ownership, rogue uvicorn killer, PID file management.
Prevents duplicate gateway instances and port conflicts.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PID_FILE = Path("/tmp/ailab-gateway.pid")
GATEWAY_PORT = 8008
GATEWAY_MARKER = "openai_gateway.py"


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _extract_pid_from_ss(line: str) -> str:
    import re
    match = re.search(r"pid=(\d+)", line)
    return match.group(1) if match else ""


def _get_cmdline(pid: str) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_text().replace("\x00", " ").strip()
    except OSError:
        return ""


def acquire_lock() -> bool:
    if PID_FILE.exists():
        try:
            stale_pid = int(PID_FILE.read_text().strip())
            if _process_alive(stale_pid):
                print(f"FATAL: Gateway already running with PID {stale_pid}", flush=True)
                return False
            print(f"Stale PID file found (PID {stale_pid} dead), cleaning up", flush=True)
            PID_FILE.unlink(missing_ok=True)
        except (ValueError, OSError):
            PID_FILE.unlink(missing_ok=True)

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    print(f"Gateway PID lock acquired: {os.getpid()}", flush=True)
    return True


def release_lock() -> None:
    PID_FILE.unlink(missing_ok=True)
    print(f"Gateway PID lock released: {os.getpid()}", flush=True)


def kill_rogue_on_port(port: int = GATEWAY_PORT) -> int:
    killed = 0
    try:
        result = subprocess.run(
            ["ss", "-tlnp", "sport", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
    except Exception:
        return 0

    for line in result.stdout.split("\n"):
        if f":{port}" not in line:
            continue
        if "uvicorn" in line or "python" in line:
            pid_str = _extract_pid_from_ss(line)
            if not pid_str or pid_str == str(os.getpid()):
                continue
            cmdline = _get_cmdline(pid_str)
            if GATEWAY_MARKER in cmdline:
                continue
            try:
                pid = int(pid_str)
                os.kill(pid, signal.SIGKILL)
                print(f"Killed rogue process PID {pid} on port {port}: {cmdline[:100]}", flush=True)
                killed += 1
            except OSError:
                pass

    if killed > 0:
        time.sleep(2)
    return killed


def prebind_cleanup(port: int = GATEWAY_PORT) -> bool:
    killed = kill_rogue_on_port(port)
    if killed > 0:
        print(f"Pre-bind cleanup: killed {killed} rogue process(es) on port {port}", flush=True)
    return True


def current_pid() -> int:
    return os.getpid()


def get_lock_info() -> dict:
    return {
        "pid_file": str(PID_FILE),
        "lock_held": PID_FILE.exists() and str(os.getpid()) in (PID_FILE.read_text() if PID_FILE.exists() else ""),
        "current_pid": os.getpid(),
        "port": GATEWAY_PORT,
    }
