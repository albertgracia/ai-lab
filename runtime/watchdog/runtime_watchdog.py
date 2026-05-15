"""Runtime Watchdog — lightweight health monitor for critical services.

Runs fast HTTP + subprocess checks against every core service.
Returns a top-level status (good / degraded / critical) plus
per-service booleans.

Designed to be called by /api/watchdog (Live API).
"""

import subprocess, time


def _http_ok(url: str, timeout: int = 3) -> bool:
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def _docker_ok() -> bool:
    try:
        r = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0 and len(r.stdout.strip()) > 0
    except Exception:
        return False


def _gpu_ok() -> bool:
    try:
        from pathlib import Path
        import json
        f = Path("/opt/ai-lab/runtime/state/cluster_state.json")
        if not f.exists():
            return False
        state = json.loads(f.read_text())
        discovered = state.get("discovered_nodes", [])
        return any(n.get("online") for n in discovered)
    except Exception:
        return False


def run_watchdog() -> dict:
    checks = {
        "gateway":      _http_ok("http://localhost:8008/health"),
        "router":       _http_ok("http://localhost:8083/health"),
        "live_api":     _http_ok("http://localhost:8084/api/status.json"),
        "docs":         _http_ok("http://localhost:4322/"),
        "docker":       _docker_ok(),
        "gpu_telemetry": _gpu_ok(),
    }
    ok = sum(1 for v in checks.values() if v)
    total = len(checks)
    if ok == total:
        status = "good"
    elif ok >= total - 2:
        status = "degraded"
    else:
        status = "critical"
    return {"status": status, "checks": checks, "timestamp": int(time.time())}
