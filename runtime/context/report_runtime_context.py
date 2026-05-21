import json
import re
import socket
import urllib.parse
from pathlib import Path
from typing import Any

REPORT_MAX_CHARS: int = 16_000

_CONFIG_DIR = Path("/opt/ai-lab/config")

_PRIMARY_RUNTIME_IP = "192.168.1.30"
_RUNTIME_HOSTNAME = "ubuntu-ialab"
_INFERENCE_BACKEND_IPS = frozenset({"192.168.1.50"})
_INVENTORY_IPS = frozenset({"192.168.1.60"})


def _resolve_hostname(host: str) -> str | None:
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None


def classify_target_role(ip_or_host: str) -> str:
    clean = ip_or_host.strip().lower()
    if clean == _RUNTIME_HOSTNAME or clean == _PRIMARY_RUNTIME_IP:
        return "primary-control-plane"
    resolved = _resolve_hostname(clean) if not clean.replace(".", "").isdigit() else clean
    target = resolved or clean
    if target == _PRIMARY_RUNTIME_IP:
        return "primary-control-plane"
    if target in _INFERENCE_BACKEND_IPS:
        return "inference-backend-gpu"
    if target in _INVENTORY_IPS:
        return "inventory-offline"
    return "unknown"


def runtime_identity() -> dict[str, Any]:
    return {
        "runtime_identity": f"{_RUNTIME_HOSTNAME}@{_PRIMARY_RUNTIME_IP}",
        "runtime_hostname": _RUNTIME_HOSTNAME,
        "primary_runtime_ip": _PRIMARY_RUNTIME_IP,
        "primary_runtime_role": "primary-control-plane",
    }


_IP_RE = re.compile(
    r"\b(?:https?://)?"
    r"(?:"
    r"(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?"
    r"|"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*"
    r"\.[a-zA-Z]{2,}(?::\d+)?"
    r")\b"
)


_EXPLICIT_IP_RE = re.compile(
    r"(?:^|\s)((?:\d{1,3}\.){3}\d{1,3})(?::\d+)?(?:\s|$|\.)"
)


def extract_target_ip(text: str) -> str | None:
    if not text:
        return None
    match = _IP_RE.search(text)
    if not match:
        return None
    raw = match.group(0).strip()
    try:
        if raw.startswith("http://") or raw.startswith("https://"):
            parsed = urllib.parse.urlparse(raw)
            host = parsed.hostname or raw
            return f"{host}:{parsed.port}" if parsed.port else host
        elif "://" in raw:
            return raw.split("://", 1)[1]
        return raw
    except Exception:
        return raw


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None
    return None


def _get_active_models() -> list[dict[str, Any]]:
    return [
        {"id": "llama-3.1-8b-instruct", "role": "lightweight / greetings / observe"},
        {"id": "qwen2.5-coder-14b-instruct", "role": "coding / report / reasoning / creative"},
        {"id": "text-embedding-nomic-embed-text-v1.5", "role": "embeddings / semantic recall"},
    ]


def _get_disabled_models() -> list[dict[str, Any]]:
    return [
        {
            "id": "qwen/qwen3.6-27b",
            "disabled_reason": "Removed from active runtime in FASE 29.3",
            "note": "Loaded in LM Studio but NOT routeable. Not recommended, not active, not available for inference.",
        }
    ]


def _get_discovered_models() -> list[dict[str, Any]]:
    return [
        {
            "id": "lmstudio-community/qwen2.5-coder-14b-instruct",
            "note": "Alternate namespace of active model qwen2.5-coder-14b-instruct",
        }
    ]


def _get_active_nodes() -> list[dict[str, Any]]:
    return [
        {
            "name": "RX9070",
            "role": "primary inference runtime",
            "status": "online",
            "vram_gb": 16,
            "host": "192.168.1.50",
        }
    ]


def _get_inventory_nodes() -> list[dict[str, Any]]:
    return [
        {
            "name": "RX7900XT",
            "role": "future dedicated backend",
            "status": "offline",
            "active_runtime": False,
            "vram_gb": 20,
            "host": "192.168.1.60",
            "note": "Node powered off. Does not affect active runtime stability. Inventoried only.",
        }
    ]


def _get_core_services() -> list[str]:
    return ["ailab-gateway (:8008)", "ailab-router (:8083)", "ailab-live-api (:8084)"]


def _get_support_services() -> list[str]:
    return ["ailab-docs (:4322)", "ailab-heartbeat", "ailab-metrics (:3010)", "ailab-runner"]


def _get_observability_services() -> list[dict[str, Any]]:
    return [
        {"name": "prometheus", "url": "http://192.168.1.40:9090", "role": "metrics TSDB + alerting"},
        {"name": "grafana", "url": "http://192.168.1.40:3000", "role": "dashboards + provisioning"},
    ]


def build_report_runtime_context(target_ip: str | None = None) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    observed: list[str] = []
    inferred: list[str] = []
    missing: list[str] = []

    rid = runtime_identity()
    ctx.update(rid)
    observed.extend(["runtime_identity", "runtime_hostname", "primary_runtime_ip", "primary_runtime_role"])

    if target_ip:
        clean_target = target_ip.strip().lower()
        role = classify_target_role(clean_target)
        match = role == "primary-control-plane"
        ctx["target_runtime_ip"] = clean_target
        ctx["target_runtime_role"] = role
        ctx["target_runtime_match"] = match
        observed.append("target_runtime_ip")
        observed.append("target_runtime_role")
        observed.append("target_runtime_match")

    try:
        from runtime.state.runtime_state import get_runtime_state
        state = get_runtime_state()
        if state:
            ctx["runtime"] = state.get("runtime", "AI-LAB Cognitive Runtime")
            ctx["status"] = state.get("status", "unknown")
            ctx["mode"] = state.get("mode", "unknown")
            ctx["active_sessions"] = state.get("active_sessions", 0)
            ctx["active_streams"] = state.get("active_streams", 0)
            ctx["executions"] = state.get("executions", 0)
            ctx["last_model"] = state.get("last_model")
            observed.extend(["runtime", "status", "mode", "active_sessions", "active_streams", "executions", "last_model"])
    except Exception:
        missing.append("runtime_state")

    try:
        from runtime.distributed.runtime_topology import get_topology
        topo = get_topology()
        if topo:
            gw = topo.get("gateway", {})
            be = topo.get("backend", {})
            ctx["gateway"] = {"host": gw.get("host", "?"), "port": gw.get("port", 0)}
            ctx["backend"] = {"host": be.get("host", "?"), "port": be.get("port", 0)}
            observed.extend(["gateway", "backend"])
    except Exception:
        missing.append("topology")

    try:
        from runtime.analytics.health_score import calculate
        hs = calculate()
        if hs:
            ctx["health_score"] = hs.get("score", 0)
            ctx["health_level"] = hs.get("level", "unknown")
            ctx["health_reasons"] = hs.get("reasons", [])
            observed.extend(["health_score", "health_level", "health_reasons"])
    except Exception:
        missing.append("health_score")

    # FASE 30I: Runtime Sensor Fusion — observed + derived + topology
    try:
        from runtime.context.sensor_fusion import SensorFusionEngine
        _engine = SensorFusionEngine()
        _snap = _engine.collect()

        _snap_dict = _snap.to_dict(max_chars=8000)
        ctx["sensor_snapshot"] = _snap_dict

        ctx["runtime_topology"] = _snap.topology.to_dict()
        ctx["domain_confidence"] = _snap.domain_confidence

        for dom, state in _snap.derived_state.items():
            if dom in ("gpu_nodes", "gateway", "control_plane", "system_node", "lmstudio_models"):
                ctx[f"sensor_{dom}"] = state

        observed.append("sensor_snapshot")
        observed.append("runtime_topology")
        observed.append("domain_confidence")

        # enrich evidence_catalog with sensor data
        ctx.setdefault("evidence_catalog", {})
        ctx["evidence_catalog"]["gpu_online"] = any(
            g.get("expected_offline") is False or g.get("status") == "online"
            for g in _snap.topology.active_gpus
        )
        ctx["evidence_catalog"]["prometheus_targets"] = {
            "total": len(_snap.observed_sources) + len(_snap.missing_sources),
            "up": len(_snap.observed_sources),
            "expected_offline": [t.get("name", t.get("job", "?")) for t in _snap.expected_offline_targets],
            "unexpected_down": [t.get("name", t.get("job", "?")) for t in _snap.unexpected_down_targets],
        }

        # operational summary
        try:
            from runtime.context.summary_builder import OperationalSummaryBuilder
            _route_family = "report"
            _summary = OperationalSummaryBuilder.build(_snap, _route_family)
            if _summary:
                ctx["operational_summary"] = _summary
                observed.append("operational_summary")
        except Exception:
            missing.append("operational_summary")

        # update context size metric
        try:
            from runtime.telemetry.prometheus_metrics import (
                record_observed_runtime_size,
                record_sensor_fusion,
                record_sensor_fusion_duration,
            )
            import json as _size_json
            _ctx_json = _size_json.dumps(ctx, ensure_ascii=False, default=str)
            record_observed_runtime_size(len(_ctx_json))
            record_sensor_fusion("all", "ok")
        except ImportError:
            pass

    except Exception:
        missing.append("sensor_fusion")

    ctx["inference_nodes"] = {
        "active": _get_active_nodes(),
        "inventory": _get_inventory_nodes(),
    }
    observed.extend(["inference_nodes.active", "inference_nodes.inventory"])

    ctx["models"] = {
        "active": _get_active_models(),
        "disabled": _get_disabled_models(),
        "discovered": _get_discovered_models(),
    }
    observed.extend(["models.active", "models.disabled", "models.discovered"])

    ctx["services"] = {
        "core": _get_core_services(),
        "support": _get_support_services(),
        "observability": _get_observability_services(),
    }
    observed.extend(["services.core", "services.support", "services.observability"])

    try:
        profile_manifest = _CONFIG_DIR.parent / "runtime" / "profiles" / "manifest_profiles.json"
        mdata = _safe_read_json(profile_manifest)
        if mdata:
            profiles = list(mdata.get("profiles", {}).keys()) if isinstance(mdata.get("profiles"), dict) else []
            ctx["profiles_available"] = profiles
            observed.append("profiles_available")
    except Exception:
        missing.append("profile_manifest")

    ctx["data_quality"] = {
        "observed_fields": observed,
        "inferred_fields": inferred,
        "missing_fields": missing,
    }

    # FASE 30H: expose evidence_catalog for evidence guard
    ctx["evidence_catalog"] = {
        "models": {
            "active": [m.get("id") for m in ctx.get("models", {}).get("active", []) if isinstance(m, dict)],
            "disabled": [m.get("id") for m in ctx.get("models", {}).get("disabled", []) if isinstance(m, dict)],
            "discovered": [m.get("id") for m in ctx.get("models", {}).get("discovered", []) if isinstance(m, dict)],
        },
        "nodes": {
            "active": [
                {"name": n.get("name"), "host": n.get("host")}
                for n in ctx.get("inference_nodes", {}).get("active", [])
                if isinstance(n, dict)
            ],
            "inventory": [
                {"name": n.get("name"), "host": n.get("host")}
                for n in ctx.get("inference_nodes", {}).get("inventory", [])
                if isinstance(n, dict)
            ],
        },
        "hosts": {
            "primary_runtime_ip": ctx.get("primary_runtime_ip"),
            "runtime_hostname": ctx.get("runtime_hostname"),
        },
        "services": ctx.get("services", {}),
    }

    ctx["_report_type"] = "runtime_operational_report"
    ctx["_runtime_generation"] = "29.4.3"
    ctx["_grounded_runtime"] = True
    ctx["_grounding_confidence"] = "high"

    return ctx


def format_report_runtime_context(target_ip: str | None = None) -> str:
    ctx = build_report_runtime_context(target_ip=target_ip)
    snapshot = json.dumps(ctx, ensure_ascii=False, default=str)
    if len(snapshot) > REPORT_MAX_CHARS:
        oversize = set(ctx.get("data_quality", {}).get("observed_fields", []))
        for costly in ("health_reasons",):
            if costly in ctx:
                del ctx[costly]
                if costly in oversize:
                    oversize.discard(costly)
        ctx["data_quality"]["observed_fields"] = list(oversize)
        snapshot = json.dumps(ctx, ensure_ascii=False, default=str)
        if len(snapshot) > REPORT_MAX_CHARS:
            snapshot = snapshot[:REPORT_MAX_CHARS] + ',"_truncated":true}'
    return snapshot
