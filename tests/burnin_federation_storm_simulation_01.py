"""FEDERATION-STORM-SIMULATION-01: bounded federation storm simulation burn-in.

Validates cognitive guards behavior under sustained federation pressure:
- replay amplification protection
- evidence reuse storms
- propagation cascades
- federation fan-out pressure
- guard degradations (DEGRADED -> CONSTRAINED -> SAFE_MODE)
- storm cooldown recovery
- lineage depth escalation
- propagation cap saturation
- recovery back to NORMAL

Duration: configurable via env BURNIN_DURATION_MINUTES (default 20, max 45).
No autonomy, no routing mutation, no persistence.
Guards only annotate metadata, limit propagation, expose observability.

Run:
  python3 tests/burnin_federation_storm_simulation_01.py
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "/opt/ai-lab")

DURATION_MINUTES = max(5, min(45, int(os.getenv("BURNIN_DURATION_MINUTES", "20"))))
MAX_WORKERS = 4
STALL_WARNING_SECONDS = 90

GATEWAY = os.getenv("BURNIN_GATEWAY_URL", "http://192.168.1.30:8008")
PROMETHEUS = os.getenv("BURNIN_PROMETHEUS_URL", "http://192.168.1.40:9090")
LMSTUDIO = os.getenv("BURNIN_LMSTUDIO_URL", "http://192.168.1.50:1234/v1").rstrip("/")
GRAFANA = os.getenv("BURNIN_GRAFANA_URL", "http://192.168.1.40:3000")
GITNEXUS = os.getenv("BURNIN_GITNEXUS_URL", "http://gitnexus.ai-lab.local:4747")

CHAT_URL = f"{LMSTUDIO}/chat/completions"
MODELS_URL = f"{LMSTUDIO}/models"

from runtime.federation.federation_guards import (
    FederationPropagationCaps,
    observe_federation_metadata_for_cognitive_guards,
    reset_federation_cognitive_guards_state,
    get_federation_guard_summary,
    get_federation_guard_runtime_state,
)
from runtime.federation.federation_observability import (
    reset_federation_observability_state,
    observe_evidence_id,
    record_evidence_lineage,
    get_evidence_summary,
)
from runtime.federation.evidence_lineage import (
    EvidenceSourceType,
    EvidenceOrigin,
    EvidenceAuthorityBinding,
    build_evidence_envelope,
    build_lineage_summary,
)
from runtime.models.model_registry import (
    DEPRECATED_QWEN_14B_ALIAS as MODEL_DEPRECATED,
    MODEL_LLAMA_8B as MODEL_LLAMA,
    MODEL_QWEN_14B as MODEL_QWEN,
)

_MODEL_CANONICAL = MODEL_QWEN
_MODEL_FASTPATH = MODEL_LLAMA

_lock = threading.Lock()
_results: dict[str, list] = {
    "guard_snapshots": [],
    "evidence_snapshots": [],
    "registry_snapshots": [],
    "prometheus_snapshots": [],
    "lmstudio_snapshots": [],
    "resource_snapshots": [],
    "chart_snapshots": [],
    "replay_storms": [],
    "propagation_storms": [],
    "storm_heuristic_events": [],
    "recovery_validations": [],
    "errors": [],
}
_cancelled = threading.Event()

STORM_EVIDENCE_IDS = [
    "replay-storm-a1",
    "replay-storm-a2",
    "replay-storm-a3",
    "propagation-b1",
    "propagation-b2",
    "propagation-b3",
    "storm-c1",
    "storm-c2",
    "storm-c3",
]
STORM_DOMAINS = ["observability", "semantic", "memory", "authority", "infrastructure"]
STORM_PAYLOAD = {"simulation": "federation-storm-01", "contract": "CG-01"}
_origin = EvidenceOrigin(
    source_domain="storm-simulation",
    source_role="simulation",
    model_profile="burnin",
    tool_name="federation-storm",
    trust_scope="simulation",
)
_auth_binding = EvidenceAuthorityBinding(
    authority_bound=False,
    authority_domain="",
    binding_reason="simulated",
)

ENVELOPE_SOURCE_MAP = {
    "observability": EvidenceSourceType.OBSERVABILITY,
    "semantic": EvidenceSourceType.SEMANTIC,
    "memory": EvidenceSourceType.MEMORY,
    "authority": EvidenceSourceType.AUTHORITY,
    "infrastructure": EvidenceSourceType.INFRASTRUCTURE,
}

_caps = FederationPropagationCaps(
    max_lineage_depth=3,
    max_replay_reuse=6,
    max_propagation_fanout=8,
    max_authority_escalation=3,
    max_evidence_reuse_rate=8,
    reuse_window_seconds=30,
    event_window_seconds=60,
    constrained_cooldown_seconds=30,
    safe_mode_cooldown_seconds=60,
)


def _req():
    import requests
    return requests


def _ts() -> float:
    return time.time()


def _elapsed(start: float) -> str:
    secs = time.time() - start
    m, s = divmod(int(secs), 60)
    return f"{m:02d}:{s:02d}"


def _record(key: str, data: dict) -> None:
    with _lock:
        _results[key].append(data)


def _record_error(source: str, message: str, detail: str = "") -> None:
    with _lock:
        _results["errors"].append({"ts": _ts(), "source": source, "message": message, "detail": detail})


def _chat_payload(model: str, *, stream: bool) -> dict:
    return {
        "model": model,
        "stream": stream,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with a single short word."},
        ],
        "max_tokens": 8,
        "temperature": 0.0,
    }


def do_completion(cycle: int, model: str, stream: bool) -> dict:
    requests = _req()
    t0 = _ts()
    try:
        timeout = 25 if stream else 15
        if stream:
            chunks = 0
            with requests.post(CHAT_URL, json=_chat_payload(model, stream=True), stream=True, timeout=timeout) as r:
                r.raise_for_status()
                for raw in r.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    line = raw.strip()
                    if line.startswith("data:"):
                        chunks += 1
            latency = (_ts() - t0) * 1000
            return {"ts": t0, "cycle": cycle, "model": model, "stream": True, "latency_ms": round(latency, 1), "chunks": chunks, "ok": True}
        else:
            r = requests.post(CHAT_URL, json=_chat_payload(model, stream=False), timeout=timeout)
            r.raise_for_status()
            latency = (_ts() - t0) * 1000
            return {"ts": t0, "cycle": cycle, "model": model, "stream": False, "latency_ms": round(latency, 1), "ok": True}
    except Exception as e:
        latency = (_ts() - t0) * 1000
        return {"ts": t0, "cycle": cycle, "model": model, "stream": stream, "latency_ms": round(latency, 1), "ok": False, "error": str(e)}


def do_health_check(endpoint: str, timeout: int = 5) -> dict:
    requests = _req()
    t0 = _ts()
    try:
        r = requests.get(f"{GATEWAY}{endpoint}", timeout=timeout)
        dt = (_ts() - t0) * 1000
        ok = r.status_code == 200
        data = r.json() if ok else {}
        return {"ok": ok, "latency_ms": round(dt, 1), "data": data, "endpoint": endpoint}
    except Exception as e:
        dt = (_ts() - t0) * 1000
        return {"ok": False, "latency_ms": round(dt, 1), "error": str(e), "endpoint": endpoint}


def do_prometheus_check() -> dict:
    requests = _req()
    queries = {
        "gateway_up": "up{job='ai-lab-gateway'}",
        "guard_state": "ailab_federation_guard_state",
        "guard_caps": "ailab_federation_guard_caps_applied_total",
        "guard_replay": "ailab_federation_guard_replay_detections_total",
        "guard_storm": "ailab_federation_guard_storm_detections_total",
        "guard_authority": "ailab_federation_guard_authority_escalations_total",
        "evidence_props": "ailab_evidence_propagations_total",
        "evidence_reuse": "ailab_evidence_reuse_total",
        "evidence_stale": "ailab_evidence_stale_total",
        "evidence_replay_risk": "ailab_evidence_replay_risk_total",
        "evidence_depth": "ailab_evidence_lineage_depth_max",
        "evidence_stored": "ailab_evidence_stored_total",
        "registry_models": "ailab_registry_models_total",
        "lmstudio_up": "ailab_lmstudio_up",
    }
    results = {}
    all_ok = True
    for name, query in queries.items():
        try:
            r = requests.get(f"{PROMETHEUS}/api/v1/query", params={"query": query}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    result = data.get("data", {}).get("result", [])
                    results[name] = result[0]["value"][1] if result else None
                else:
                    results[name] = None
                    all_ok = False
            else:
                results[name] = None
                all_ok = False
        except Exception:
            results[name] = None
            all_ok = False
    return {"ok": all_ok, "results": results}


def do_lmstudio_models_check() -> dict:
    requests = _req()
    try:
        t0 = _ts()
        r = requests.get(MODELS_URL, timeout=5)
        dt = (_ts() - t0) * 1000
        if r.status_code != 200:
            return {"ok": False, "latency_ms": round(dt, 1), "error": f"status={r.status_code}"}
        data = r.json() or {}
        ids = [d.get("id") for d in (data.get("data") or []) if isinstance(d, dict)]
        return {
            "ok": True,
            "latency_ms": round(dt, 1),
            "models": ids,
            "has_canonical": MODEL_QWEN in ids,
            "has_deprecated": MODEL_DEPRECATED in ids,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_resource_snapshot(pid: int) -> dict:
    try:
        with open(f"/proc/{pid}/status") as f:
            raw = f.read()
        vm_rss_kb = 0
        for line in raw.splitlines():
            if line.startswith("VmRSS:"):
                vm_rss_kb = int(line.split()[1])
                break
        return {"ts": _ts(), "rss_kb": vm_rss_kb}
    except Exception:
        return {"ts": _ts(), "rss_kb": 0}


def do_gitnexus_check() -> dict:
    requests = _req()
    try:
        t0 = _ts()
        r = requests.get(f"{GITNEXUS}/api/health", timeout=5)
        dt = (_ts() - t0) * 1000
        return {"ok": r.status_code == 200, "latency_ms": round(dt, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_grafana_check() -> dict:
    requests = _req()
    try:
        t0 = _ts()
        r = requests.get(f"{GRAFANA}/api/health", timeout=5)
        dt = (_ts() - t0) * 1000
        return {"ok": r.status_code == 200, "latency_ms": round(dt, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def reset_guards_state() -> dict:
    try:
        reset_federation_cognitive_guards_state()
        reset_federation_observability_state()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_guard_snapshot() -> dict:
    try:
        summary = get_federation_guard_summary()
        state = get_federation_guard_runtime_state()
        return {"ok": True, "summary": summary, "state": state}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_evidence_snapshot() -> dict:
    try:
        summary = get_evidence_summary()
        return {"ok": True, "summary": summary}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Storm Simulation Workers ──────────────────────────────────────────────

def simulate_replay_pressure(cycle: int) -> dict:
    """Reuse evidence IDs repeatedly within a short window.
    
    Goal: trigger replay_detected events, reuse counters, propagate caps.
    """
    results = []
    events = []
    eid = STORM_EVIDENCE_IDS[cycle % 3]
    for i in range(4):
        meta = {
            "_evidence_id": eid,
            "_evidence_lineage_depth": 1,
            "_evidence_reuse_count": 5 + i,
            "_domain": STORM_DOMAINS[i % len(STORM_DOMAINS)],
            "_federation": {"domain": STORM_DOMAINS[i % len(STORM_DOMAINS)], "authority_weight": "low"},
            "_propagation_fanout": 2,
        }
        now = _ts()
        out = observe_federation_metadata_for_cognitive_guards(meta, caps=_caps, now=now)
        guard = out.get("_cognitive_guard", {})
        events.append({
            "evidence_id": eid,
            "state": guard.get("state", ""),
            "degraded": guard.get("degraded", False),
            "caps_applied": list(guard.get("caps_applied", [])),
        })
        
        prev = observe_evidence_id(eid)
        envelope = build_evidence_envelope(
            evidence_type="simulation",
            source_type=EvidenceSourceType.OBSERVABILITY,
            canonical_payload=STORM_PAYLOAD,
            origin=_origin,
            authority_binding=_auth_binding,
            previous_seen_count=prev,
            freshness_seconds=10,
            max_depth=3,
        )
        summary = build_lineage_summary(envelope.envelope).to_dict()
        record_evidence_lineage(evidence_summary=summary)
        results.append(summary)

    return {
        "cycle": cycle,
        "evidence_id": eid,
        "events": events,
        "results_count": len(results),
    }


def simulate_propagation_cascade(cycle: int) -> dict:
    """Concurrent requests with reused federation metadata and growing depth.
    
    Goal: activate propagation_cap_applied, lineage depth growth, evidence reuse.
    """
    results = []
    events = []
    depth = min(1 + (cycle % 8), 7)
    fanout = min(2 + (cycle % 5), 10)
    eid = STORM_EVIDENCE_IDS[3 + (cycle % 3)]
    
    meta = {
        "_evidence_id": eid,
        "_evidence_lineage_depth": depth,
        "_evidence_reuse_count": 2 + (cycle % 6),
        "_domain": STORM_DOMAINS[cycle % len(STORM_DOMAINS)],
        "_federation": {
            "domain": STORM_DOMAINS[cycle % len(STORM_DOMAINS)],
            "authority_weight": "high" if cycle % 3 == 0 else "low",
        },
        "_propagation_fanout": fanout,
    }
    now = _ts()
    out = observe_federation_metadata_for_cognitive_guards(meta, caps=_caps, now=now)
    guard = out.get("_cognitive_guard", {})
    events.append({
        "evidence_id": eid,
        "state": guard.get("state", ""),
        "degraded": guard.get("degraded", False),
        "caps_applied": list(guard.get("caps_applied", [])),
        "lineage_depth": depth,
        "propagation_fanout": fanout,
    })
    
    for i in range(3):
        prev = observe_evidence_id(eid)
        envelope = build_evidence_envelope(
            evidence_type="propagation",
            source_type=ENVELOPE_SOURCE_MAP.get(STORM_DOMAINS[cycle % len(STORM_DOMAINS)], EvidenceSourceType.UNKNOWN),
            canonical_payload=STORM_PAYLOAD,
            origin=_origin,
            authority_binding=_auth_binding,
            parent_evidence_ids=[eid] if i > 0 else [],
            lineage_depth=depth,
            previous_seen_count=prev,
            freshness_seconds=30,
            max_depth=3,
        )
        summary = build_lineage_summary(envelope.envelope).to_dict()
        record_evidence_lineage(evidence_summary=summary)
        results.append(summary)

    return {
        "cycle": cycle,
        "evidence_id": eid,
        "events": events,
        "depth": depth,
        "fanout": fanout,
        "results_count": len(results),
        "authority_escalated": cycle % 3 == 0,
    }


def simulate_storm_heuristic(cycle: int) -> dict:
    """Concentrate bursts within guard window to trigger storm detection.
    
    Goal: force DEGRADED -> CONSTRAINED -> SAFE_MODE transitions.
    """
    results = []
    events = []
    eid = STORM_EVIDENCE_IDS[6 + (cycle % 3)]
    
    for i in range(10):
        meta = {
            "_evidence_id": eid,
            "_evidence_lineage_depth": 1,
            "_evidence_reuse_count": 0,
            "_domain": STORM_DOMAINS[cycle % len(STORM_DOMAINS)],
            "_federation": {
                "domain": STORM_DOMAINS[cycle % len(STORM_DOMAINS)],
                "authority_weight": "low",
            },
            "_propagation_fanout": 1 + (i % 3),
        }
        now = _ts() + (i * 0.1)
        out = observe_federation_metadata_for_cognitive_guards(meta, caps=_caps, now=now)
        guard = out.get("_cognitive_guard", {})
        events.append({
            "evidence_id": eid,
            "state": guard.get("state", ""),
            "degraded": guard.get("degraded", False),
            "caps_applied": list(guard.get("caps_applied", [])),
        })

    return {
        "cycle": cycle,
        "evidence_id": eid,
        "events": events,
        "events_count": len(events),
    }


def do_recovery_validation() -> dict:
    """Validate that guards recover to NORMAL after pressure stops."""
    initial = do_guard_snapshot()
    start_wait = _ts()
    while _ts() - start_wait < 15:
        snap = do_guard_snapshot()
        if snap.get("ok"):
            state = snap.get("state", {}).get("state", "") or snap.get("summary", {}).get("state", {}).get("state", "")
            if state == "NORMAL":
                elapsed = round(_ts() - start_wait, 1)
                return {"ok": True, "recovered_to": "NORMAL", "elapsed_seconds": elapsed, "initial_state": initial}
        time.sleep(1)
    final = do_guard_snapshot()
    return {"ok": False, "recovered_to": "TIMEOUT", "elapsed_seconds": 15, "initial_state": initial, "final_state": final}


# ── Fail conditions ───────────────────────────────────────────────────────

_FAIL_CONDITIONS: list[str] = []


def check_fail_conditions() -> list[str]:
    fails: list[str] = []
    with _lock:
        errors = list(_results["errors"])
        guard_snaps = list(_results["guard_snapshots"])

    if len(errors) > 0:
        for e in errors[-10:]:
            if "repeated" in e.get("message", "").lower():
                fails.append(f"REPEATED_DEADLOCK: {e['source']}: {e['message']}")

    with _lock:
        lmstudio_snaps = list(_results["lmstudio_snapshots"])
    for snap in lmstudio_snaps:
        if snap.get("has_deprecated"):
            fails.append(f"DEPRECATED_ALIAS_RESURRECTION at ts={snap.get('ts', 0)}")
            break

    for snap in guard_snaps:
        data = snap.get("data", {})
        payload = data if isinstance(data, dict) else {}
        summary = payload.get("summary") if isinstance(payload, dict) else {}
        state_obj = summary.get("state") if isinstance(summary, dict) else {}
        state_val = state_obj.get("state") if isinstance(state_obj, dict) else ""
        counters = summary.get("counters") if isinstance(summary, dict) else {}
        transitions = 0
        if isinstance(counters, dict):
            transitions = int(counters.get("state_transitions_total", 0) or 0)
        if state_val == "SAFE_MODE" and transitions > 10:
            fails.append(f"SAFE_MODE_LOOP: {transitions} transitions")
            break

    with _lock:
        recovery_vals = list(_results["recovery_validations"])
    for rv in recovery_vals:
        if not rv.get("ok"):
            fails.append(f"RECOVERY_FAILED: {rv.get('recovered_to', 'unknown')} after {rv.get('elapsed_seconds', 0)}s")
            break

    return fails


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    global _cancelled
    start_ts = _ts()
    duration_secs = DURATION_MINUTES * 60
    print("=" * 60)
    print("FEDERATION STORM SIMULATION 01")
    print(f"Duration: {DURATION_MINUTES} min ({duration_secs}s)")
    print(f"Gateway:  {GATEWAY}")
    print(f"LMStudio: {LMSTUDIO}")
    print(f"Prometheus: {PROMETHEUS}")
    print(f"Grafana: {GRAFANA}")
    print(f"GitNexus: {GITNEXUS}")
    print(f"Models:   canonical={_MODEL_CANONICAL}, fastpath={_MODEL_FASTPATH}")
    print("=" * 60)

    requests = _req()

    # 0. Gateway health + PID
    gateway_pid = 0
    try:
        r = requests.get(f"{GATEWAY}/health", timeout=5)
        if r.status_code == 200:
            print(f"[{_elapsed(start_ts)}] Gateway health OK")
    except Exception as e:
        print(f"[{_elapsed(start_ts)}] FAIL gateway unreachable: {e}")
        return 2

    for pid_str in os.listdir("/proc"):
        if not pid_str.isdigit():
            continue
        try:
            with open(f"/proc/{pid_str}/cmdline") as f:
                cmd = f.read()
            if "openai_gateway.py" in cmd:
                gateway_pid = int(pid_str)
                break
        except Exception:
            continue
    if gateway_pid:
        print(f"[{_elapsed(start_ts)}] Gateway PID: {gateway_pid}")
    else:
        print(f"[{_elapsed(start_ts)}] WARNING: could not find gateway PID")

    # 1. Pre-flight checks
    print(f"\n── Pre-flight checks ──")
    preflight_ok = True
    for ep in ["/health", "/runtime/models/registry", "/runtime/guards/summary", "/runtime/evidence/summary", "/runtime/guards/state"]:
        chk = do_health_check(ep)
        if chk.get("ok"):
            print(f"  OK {ep}")
        else:
            print(f"  FAIL {ep}: {chk.get('error', 'status error')}")
            preflight_ok = False

    try:
        r = requests.get(MODELS_URL, timeout=5)
        if r.status_code == 200:
            data = r.json() or {}
            ids = [d.get("id") for d in (data.get("data") or []) if isinstance(d, dict)]
            print(f"  OK /v1/models ({len(ids)} models)")
            if MODEL_DEPRECATED in ids:
                print(f"  FAIL deprecated alias present: {MODEL_DEPRECATED}")
                preflight_ok = False
        else:
            print(f"  FAIL /v1/models status={r.status_code}")
            preflight_ok = False
    except Exception as e:
        print(f"  FAIL /v1/models: {e}")
        preflight_ok = False

    try:
        r = requests.get(f"{PROMETHEUS}/api/v1/query", params={"query": "up{job='ai-lab-gateway'}"}, timeout=5)
        if r.status_code == 200 and r.json().get("status") == "success":
            print("  OK Prometheus /api/v1/query")
        else:
            print(f"  FAIL Prometheus query")
            preflight_ok = False
    except Exception as e:
        print(f"  FAIL Prometheus: {e}")
        preflight_ok = False

    try:
        r = requests.get(f"{GRAFANA}/api/health", timeout=5)
        if r.status_code == 200:
            print("  OK Grafana /api/health")
    except Exception as e:
        print(f"  WARN Grafana unreachable: {e}")

    try:
        r = requests.get(f"{GITNEXUS}/api/health", timeout=5)
        if r.status_code == 200:
            print("  OK GitNexus /api/health")
    except Exception as e:
        print(f"  WARN GitNexus unreachable: {e}")

    if not preflight_ok:
        print("\nFAIL pre-flight checks — aborting")
        return 3

    # Reset guard state before simulation
    reset_guards_state()
    print(f"\n  OK guards state reset to NORMAL")

    print(f"\n── Storm simulation running ({duration_secs}s) ──")

    # 2. Burn-in loop with storm phases
    cycle = 0
    last_progress_ts = time.time()
    storm_phase = 0
    recovery_pending = False
    recovery_attempted = False

    try:
        while time.time() - start_ts < duration_secs and not _cancelled.is_set():
            cycle += 1
            now = time.time()
            elapsed_cycle_start = now
            remaining = duration_secs - (now - start_ts)
            elapsed_total = now - start_ts

            # Print progress every 60s
            if now - last_progress_ts >= 60:
                elapsed_str = _elapsed(start_ts)
                rem_m, rem_s = divmod(int(remaining), 60)
                with _lock:
                    errs = len(_results["errors"])
                pct = ((now - start_ts) / duration_secs) * 100
                print(f"[{elapsed_str}] {pct:.0f}% done | cycle={cycle} | errors={errs} | phase={storm_phase}")
                last_progress_ts = now

            if now - last_progress_ts > STALL_WARNING_SECONDS:
                print(f"[{_elapsed(start_ts)}] WARNING: possible stall")

            # Storm phase progression
            # Phase 0-2: replay pressure
            # Phase 3-5: propagation cascade
            # Phase 6-8: storm heuristic
            # Phase 9: recovery validation
            storm_phase = (cycle // 10) % 10

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = []

                # Always run a completion for baseline health
                model = _MODEL_CANONICAL if cycle % 2 == 0 else _MODEL_FASTPATH
                futures.append(pool.submit(do_completion, cycle, model, False))

                if cycle % 3 == 0:
                    futures.append(pool.submit(do_completion, cycle, _MODEL_FASTPATH, False))

                # Storm simulation based on phase
                if storm_phase <= 2:
                    # Replay pressure
                    for si in range(3):
                        futures.append(pool.submit(simulate_replay_pressure, cycle + si))
                elif storm_phase <= 5:
                    # Propagation cascade
                    for si in range(2):
                        futures.append(pool.submit(simulate_propagation_cascade, cycle + si))
                elif storm_phase <= 8:
                    # Storm heuristic bursts
                    futures.append(pool.submit(simulate_storm_heuristic, cycle))
                    if cycle % 2 == 0:
                        futures.append(pool.submit(simulate_storm_heuristic, cycle + 1))
                else:
                    # Recovery phase: stop storm, let cooldown expire
                    if not recovery_attempted:
                        print(f"[{_elapsed(start_ts)}] Entering recovery validation phase")
                        recovery_attempted = True

                # Periodic checks
                if cycle % 2 == 0:
                    futures.append(pool.submit(do_health_check, "/runtime/guards/summary"))
                    futures.append(pool.submit(do_health_check, "/runtime/evidence/summary"))
                    futures.append(pool.submit(do_health_check, "/runtime/guards/state"))
                    futures.append(pool.submit(do_health_check, "/runtime/models/registry"))

                if cycle % 3 == 0:
                    futures.append(pool.submit(do_lmstudio_models_check))
                    futures.append(pool.submit(do_prometheus_check))

                if cycle % 5 == 0:
                    futures.append(pool.submit(do_gitnexus_check))
                    futures.append(pool.submit(do_grafana_check))

                # Recovery validation after storm phases
                if storm_phase >= 9 and not recovery_pending:
                    recovery_pending = True
                    print(f"[{_elapsed(start_ts)}] Starting recovery validation (stopping storms)...")
                    time.sleep(2)

                if storm_phase >= 9 and cycle % 15 == 0 and cycle > 20:
                    futures.append(pool.submit(do_recovery_validation))

                # Collect results
                for future in as_completed(futures, timeout=30):
                    try:
                        result = future.result()
                        if "cycle" in result and "events" in result:
                            _record("replay_storms", result)
                        elif "cycle" in result and "depth" in result:
                            _record("propagation_storms", result)
                        elif "cycle" in result and "events_count" in result:
                            _record("storm_heuristic_events", result)
                        elif "recovered_to" in result:
                            _record("recovery_validations", result)
                        elif result.get("data", {}).get("endpoint") == "runtime/guards/summary":
                            _record("guard_snapshots", result)
                        elif result.get("data", {}).get("endpoint") == "runtime/evidence/summary":
                            _record("evidence_snapshots", result)
                        elif result.get("data", {}).get("endpoint") == "runtime/models/registry":
                            _record("registry_snapshots", result)
                        elif result.get("results") and "gateway_up" in result.get("results", {}):
                            _record("prometheus_snapshots", result)
                        elif "models" in result:
                            _record("lmstudio_snapshots", result)
                        elif result.get("latency_ms") is not None and "models" not in result and "results" not in result and "data" not in result:
                            if result.get("endpoint", "").startswith("/runtime/"):
                                pass
                    except Exception as e:
                        _record_error("future", str(e))

            # Resource snapshot
            if gateway_pid > 0 and cycle % 3 == 0:
                snap = do_resource_snapshot(gateway_pid)
                _record("resource_snapshots", snap)

            # Fail condition check
            fails = check_fail_conditions()
            if fails:
                print(f"[{_elapsed(start_ts)}] FAIL conditions detected:")
                for f in fails:
                    print(f"  - {f}")
                return 4

            # Direct snapshot every 5 cycles
            if cycle % 5 == 0:
                gs = do_guard_snapshot()
                es = do_evidence_snapshot()
                _record("guard_snapshots", {"ok": gs.get("ok"), "data": {"summary": gs.get("summary", {}), "endpoint": "runtime/guards/summary"}})
                _record("evidence_snapshots", {"ok": es.get("ok"), "data": {"summary": es.get("summary", {}), "endpoint": "runtime/evidence/summary"}})

            # Throttle
            elapsed_cycle = time.time() - elapsed_cycle_start
            sleep_time = max(0, 2.5 - elapsed_cycle)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n[{_elapsed(start_ts)}] Burn-in interrupted by user")
        _cancelled.set()

    # 3. Final report
    duration_actual = time.time() - start_ts
    print(f"\n{'=' * 60}")
    print("STORM SIMULATION COMPLETE")
    print(f"{'=' * 60}")

    with _lock:
        guard_snaps = list(_results["guard_snapshots"])
        evidence_snaps = list(_results["evidence_snapshots"])
        registry_snaps = list(_results["registry_snapshots"])
        lmstudio_snaps = list(_results["lmstudio_snapshots"])
        prometheus_snaps = list(_results["prometheus_snapshots"])
        resource_snaps = list(_results["resource_snapshots"])
        replay_storms = list(_results["replay_storms"])
        prop_storms = list(_results["propagation_storms"])
        storm_events = list(_results["storm_heuristic_events"])
        recovery_vals = list(_results["recovery_validations"])
        errors = list(_results["errors"])

    # Guard state analysis
    guard_states = {}
    max_caps_applied = 0
    max_replay_detected = 0
    max_storm_detected = 0
    for snap in guard_snaps:
        data = snap.get("data", {})
        payload = data if isinstance(data, dict) else {}
        summary = payload.get("summary") if isinstance(payload, dict) else payload
        if not isinstance(summary, dict):
            continue
        state_obj = summary.get("state") if isinstance(summary, dict) else {}
        s = state_obj.get("state", "unknown") if isinstance(state_obj, dict) else "unknown"
        guard_states[s] = guard_states.get(s, 0) + 1
        counters = summary.get("counters") if isinstance(summary, dict) else {}
        if isinstance(counters, dict):
            max_caps_applied = max(max_caps_applied, int(counters.get("caps_applied_total", 0) or 0))
            max_replay_detected = max(max_replay_detected, int(counters.get("replay_detections_total", 0) or 0))
            max_storm_detected = max(max_storm_detected, int(counters.get("storm_detections_total", 0) or 0))

    # Evidence analysis
    max_depth = 0
    max_stored = 0
    total_props = 0
    total_stale = 0
    total_replay_risk = 0
    total_reuse = 0
    total_invalid = 0
    for snap in evidence_snaps:
        data = snap.get("data", {})
        summary = data if isinstance(data, dict) else {}
        if not isinstance(summary, dict):
            continue
        s = summary.get("summary") if isinstance(summary, dict) else summary
        if not isinstance(s, dict):
            continue
        max_depth = max(max_depth, int(s.get("lineage_depth_max", 0) or 0))
        max_stored = max(max_stored, int(s.get("stored_evidences", 0) or 0))
        total_props = max(total_props, int(s.get("evidence_propagations_total", 0) or 0))
        total_stale = max(total_stale, int(s.get("stale_evidence_total", 0) or 0))
        total_replay_risk = max(total_replay_risk, int(s.get("replay_risk_total", 0) or 0))
        total_reuse = max(total_reuse, int(s.get("evidence_reuse_total", 0) or 0))
        total_invalid = max(total_invalid, int(s.get("invalid_lineage_total", 0) or 0))

    # LM Studio health
    lmstudio_ok = sum(1 for s in lmstudio_snaps if s.get("ok"))
    lmstudio_fail = len(lmstudio_snaps) - lmstudio_ok
    lmstudio_deprecated = any(s.get("has_deprecated") for s in lmstudio_snaps)
    lmstudio_latencies = sorted([s.get("latency_ms", 0) for s in lmstudio_snaps if s.get("ok")])

    def percentile(data, p):
        if not data:
            return 0
        idx = max(0, min(len(data) - 1, int(len(data) * p / 100)))
        return data[idx]

    # Resource analysis
    rss_values = sorted([s["rss_kb"] for s in resource_snaps if s.get("rss_kb", 0) > 0])

    # Prometheus health
    prom_ok = sum(1 for s in prometheus_snaps if s.get("ok"))
    prom_total = len(prometheus_snaps)

    # Recovery analysis
    recovery_ok = sum(1 for rv in recovery_vals if rv.get("ok"))
    recovery_fail = len(recovery_vals) - recovery_ok

    # Compile report
    report = {
        "duration_seconds": round(duration_actual, 1),
        "duration_minutes": round(duration_actual / 60, 1),
        "total_cycles": cycle,
        "errors_total": len(errors),
        "guard_states": guard_states,
        "guard_max_caps_applied": max_caps_applied,
        "guard_max_replay_detections": max_replay_detected,
        "guard_max_storm_detections": max_storm_detected,
        "evidence": {
            "max_lineage_depth": max_depth,
            "max_stored": max_stored,
            "total_propagations": total_props,
            "total_stale": total_stale,
            "total_replay_risk": total_replay_risk,
            "total_reuse": total_reuse,
            "total_invalid_lineage": total_invalid,
        },
        "guard_snapshots_count": len(guard_snaps),
        "evidence_snapshots_count": len(evidence_snaps),
        "registry_snapshots_count": len(registry_snaps),
        "lmstudio_checks_count": len(lmstudio_snaps),
        "prometheus_checks_count": len(prometheus_snaps),
        "resource_snapshots_count": len(resource_snaps),
        "replay_storms_simulated": len(replay_storms),
        "propagation_storms_simulated": len(prop_storms),
        "storm_heuristic_bursts": len(storm_events),
        "recovery_validations": len(recovery_vals),
        "recovery_ok": recovery_ok,
        "recovery_fail": recovery_fail,
        "lmstudio": {
            "checks_ok": lmstudio_ok,
            "checks_failed": lmstudio_fail,
            "deprecated_alias_detected": lmstudio_deprecated,
            "latency_ms_p50": round(percentile(lmstudio_latencies, 50), 1) if lmstudio_latencies else 0,
            "latency_ms_p95": round(percentile(lmstudio_latencies, 95), 1) if lmstudio_latencies else 0,
        },
        "resources": {
            "rss_kb_min": min(rss_values) if rss_values else 0,
            "rss_kb_max": max(rss_values) if rss_values else 0,
            "rss_kb_avg": round(sum(rss_values) / len(rss_values), 1) if rss_values else 0,
            "rss_mb_min": round(min(rss_values) / 1024, 1) if rss_values else 0,
            "rss_mb_max": round(max(rss_values) / 1024, 1) if rss_values else 0,
            "rss_mb_avg": round(sum(rss_values) / len(rss_values) / 1024, 1) if rss_values else 0,
        },
        "prometheus": {"checks_ok": prom_ok, "checks_total": prom_total},
        "error_sources": {},
    }

    error_sources = {}
    for e in errors:
        src = e.get("source", "unknown")
        error_sources[src] = error_sources.get(src, 0) + 1
    report["error_sources"] = error_sources

    # PASS / FAIL
    pass_conditions = True
    fail_reasons = []

    if report["lmstudio"].get("deprecated_alias_detected"):
        pass_conditions = False
        fail_reasons.append("deprecated alias resurrected in LM Studio")

    if report["evidence"]["max_lineage_depth"] > 50:
        pass_conditions = False
        fail_reasons.append(f"unbounded lineage depth: {report['evidence']['max_lineage_depth']}")

    if report["evidence"]["max_stored"] > 2000:
        pass_conditions = False
        fail_reasons.append(f"unbounded evidence store: {report['evidence']['max_stored']}")

    if prom_total > 0 and prom_ok < prom_total * 0.5:
        pass_conditions = False
        fail_reasons.append(f"Prometheus scrape failure >50% ({prom_ok}/{prom_total})")

    if report["resources"]["rss_mb_max"] > 1024:
        pass_conditions = False
        fail_reasons.append(f"gateway RSS >1024MB ({report['resources']['rss_mb_max']} MB)")

    if lmstudio_fail > lmstudio_ok and lmstudio_ok + lmstudio_fail > 0:
        pass_conditions = False
        fail_reasons.append(f"LM Studio failure rate >50% ({lmstudio_fail}/{lmstudio_ok + lmstudio_fail})")

    if guard_states.get("SAFE_MODE", 0) > 10:
        pass_conditions = False
        fail_reasons.append(f"SAFE_MODE observed {guard_states.get('SAFE_MODE', 0)} times")

    if recovery_fail > 0:
        pass_conditions = False
        fail_reasons.append(f"{recovery_fail} recovery validation(s) failed")

    report["pass"] = pass_conditions
    report["fail_reasons"] = fail_reasons

    # Print report
    print(json.dumps(report, indent=2, default=str))

    # Write report file
    report_path = "/tmp/FEDERATION-STORM-SIMULATION-01.md"
    try:
        with open(report_path, "w") as f:
            f.write("# FEDERATION-STORM-SIMULATION-01 Report\n\n")
            f.write(f"- **Duration:** {report['duration_minutes']} min ({report['duration_seconds']}s)\n")
            f.write(f"- **Total cycles:** {report['total_cycles']}\n")
            f.write(f"- **Errors:** {report['errors_total']}\n")
            f.write(f"- **Replay storms simulated:** {report['replay_storms_simulated']}\n")
            f.write(f"- **Propagation storms simulated:** {report['propagation_storms_simulated']}\n")
            f.write(f"- **Storm heuristic bursts:** {report['storm_heuristic_bursts']}\n\n")

            f.write("## Guard State Transitions\n")
            for s, count in sorted(guard_states.items(), key=lambda x: -x[1]):
                f.write(f"- **{s}:** {count} snapshots\n")
            f.write(f"- Max caps applied: {report['guard_max_caps_applied']}\n")
            f.write(f"- Max replay detections: {report['guard_max_replay_detections']}\n")
            f.write(f"- Max storm detections: {report['guard_max_storm_detections']}\n\n")

            f.write("## Evidence\n")
            f.write(f"- Max lineage depth: {report['evidence']['max_lineage_depth']}\n")
            f.write(f"- Max stored: {report['evidence']['max_stored']}\n")
            f.write(f"- Total propagations: {report['evidence']['total_propagations']}\n")
            f.write(f"- Total stale: {report['evidence']['total_stale']}\n")
            f.write(f"- Total replay risk: {report['evidence']['total_replay_risk']}\n")
            f.write(f"- Total reuse: {report['evidence']['total_reuse']}\n")
            f.write(f"- Total invalid lineage: {report['evidence']['total_invalid_lineage']}\n\n")

            f.write("## Recovery Validations\n")
            f.write(f"- Total: {report['recovery_validations']}\n")
            f.write(f"- OK: {report['recovery_ok']}\n")
            f.write(f"- Failed: {report['recovery_fail']}\n\n")

            f.write("## LM Studio\n")
            f.write(f"- Checks OK: {report['lmstudio']['checks_ok']}/{report['lmstudio_checks_count']}\n")
            f.write(f"- Checks failed: {report['lmstudio']['checks_failed']}\n")
            f.write(f"- Deprecated alias detected: {report['lmstudio']['deprecated_alias_detected']}\n")
            f.write(f"- /models latency p50: {report['lmstudio']['latency_ms_p50']} ms\n")
            f.write(f"- /models latency p95: {report['lmstudio']['latency_ms_p95']} ms\n\n")

            f.write("## Resources\n")
            f.write(f"- RSS min: {report['resources']['rss_kb_min']} KB ({report['resources']['rss_mb_min']} MB)\n")
            f.write(f"- RSS max: {report['resources']['rss_kb_max']} KB ({report['resources']['rss_mb_max']} MB)\n")
            f.write(f"- RSS avg: {report['resources']['rss_kb_avg']} KB ({report['resources']['rss_mb_avg']} MB)\n\n")

            f.write("## Prometheus\n")
            f.write(f"- Checks OK: {report['prometheus']['checks_ok']}/{report['prometheus']['checks_total']}\n\n")

            f.write("## Error Sources\n")
            for src, count in sorted(error_sources.items(), key=lambda x: -x[1]):
                f.write(f"- **{src}:** {count}\n")

            f.write("\n## Verdict\n")
            if pass_conditions:
                f.write("**PASS** - federation guards bounded, stable, recovery verified\n")
            else:
                f.write("**FAIL** - condiciones de fallo detectadas:\n")
                for r in fail_reasons:
                    f.write(f"- {r}\n")
        print(f"\nReport written to {report_path}")
    except Exception as e:
        print(f"WARN: could not write report: {e}")

    if pass_conditions:
        print(f"\n{'=' * 60}")
        print("VERDICT: PASS - federation guards bounded and stable")
        print(f"{'=' * 60}")
        return 0
    else:
        print(f"\n{'=' * 60}")
        print("VERDICT: FAIL")
        for r in fail_reasons:
            print(f"  - {r}")
        print(f"{'=' * 60}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
