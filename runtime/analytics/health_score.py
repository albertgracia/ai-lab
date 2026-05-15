"""Health Score - Calculates overall cluster health 0-100."""
import time
import subprocess
import json
from pathlib import Path

STATE_DIR = Path("/opt/ai-lab/runtime/state")


def calculate():
    score = 100
    reasons = []

    # 1. GPU nodes online (max 2 nodes = +30 points)
    gpu_file = STATE_DIR / "cluster_state.json"
    gpu_online = 0
    if gpu_file.exists():
        try:
            state = json.loads(gpu_file.read_text())
            nodes = state.get("nodes", [])
            gpu_online = len([n for n in nodes if n.get("online")])
        except: pass
    score -= (2 - gpu_online) * 30
    if gpu_online < 2: reasons.append(f"{2-gpu_online} GPU(s) offline")

    # 2. Gateway check (-15 if down)
    try:
        r = subprocess.run(["curl", "-sf", "--max-time", "3", "http://localhost:8008/health"], capture_output=True, timeout=5)
        if r.returncode != 0: score -= 15; reasons.append("Gateway down")
    except: score -= 15; reasons.append("Gateway unreachable")

    # 3. Router check (-10 if down)
    try:
        r = subprocess.run(["curl", "-sf", "--max-time", "3", "http://localhost:8083/health"], capture_output=True, timeout=5)
        if r.returncode != 0: score -= 10; reasons.append("Router down")
    except: score -= 10; reasons.append("Router unreachable")

    # 4. Prometheus check (-10 if down)
    try:
        r = subprocess.run(["curl", "-sf", "--max-time", "3", "http://192.168.1.40:9090/-/healthy"], capture_output=True, timeout=5)
        if r.returncode != 0: score -= 10; reasons.append("Prometheus down")
    except: score -= 10; reasons.append("Prometheus unreachable")

    # 5. Docker containers (-5 if none running)
    try:
        r = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=5)
        running = len([l for l in r.stdout.strip().split("\n") if l])
        if running < 5: score -= 5; reasons.append(f"Only {running} containers")
    except: score -= 5; reasons.append("Docker unavailable")

    # 6. Latency penalty
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "3", "http://localhost:8008/metrics"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.split("\n"):
            if "ailab_last_latency_ms" in line and not line.startswith("#"):
                lat = float(line.split()[-1])
                if lat > 30000: score -= 20; reasons.append("High latency")
                elif lat > 10000: score -= 10; reasons.append("Elevated latency")
    except: pass

    score = max(0, min(100, score))
    return {"score": score, "reasons": reasons, "level": _level(score)}


def _level(s):
    if s >= 90: return "perfect"
    if s >= 70: return "good"
    if s >= 50: return "degraded"
    if s >= 30: return "poor"
    return "critical"
