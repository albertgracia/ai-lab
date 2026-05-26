#!/usr/bin/env python3
"""GATEWAY-SHUTDOWN-GRACEFUL-01 burn-in helper.

Read-only verification helper. It does not restart services.
Use it before and after a manual restart to confirm behavior.
"""

from __future__ import annotations

import json
import subprocess
import sys
from urllib.request import Request, urlopen


BASE = "http://127.0.0.1:8008"


def _get_json(path: str) -> dict:
    req = Request(f"{BASE}{path}")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _contains_bad_shutdown_lines() -> tuple[bool, str]:
    cmd = [
        "journalctl",
        "-u",
        "ailab-gateway",
        "-n",
        "200",
        "--no-pager",
    ]
    out = subprocess.check_output(cmd, text=True)
    bad = [
        "State 'stop-sigterm' timed out",
        "signal SIGKILL",
        "Failed with result 'timeout'",
    ]
    for line in out.splitlines():
        if any(x in line for x in bad):
            return True, line
    return False, ""


def main() -> int:
    print("GATEWAY-SHUTDOWN-GRACEFUL-01 burn-in")
    print("1) Comprobando endpoints clave...")
    health = _get_json("/health")
    models = _get_json("/v1/models")
    runtime = _get_json("/runtime/health/summary")
    print(f"   /health status={health.get('status')} shutting_down={health.get('shutting_down', False)}")
    print(f"   /v1/models count={len(models.get('data', []))}")
    print(f"   /runtime/health/summary status={runtime.get('status')} score={runtime.get('score')}")

    print("2) Revisando logs recientes de shutdown...")
    has_bad, sample = _contains_bad_shutdown_lines()
    if has_bad:
        print("   WARN: se detecto evidencia de timeout/SIGKILL en logs recientes")
        print(f"   sample: {sample}")
    else:
        print("   OK: sin evidencia de timeout/SIGKILL en las ultimas 200 lineas")

    print("3) Reinicio manual requerido para validacion completa:")
    print("   sudo systemctl restart ailab-gateway")
    print("   luego volver a ejecutar este script")

    return 0 if not has_bad else 10


if __name__ == "__main__":
    sys.exit(main())
