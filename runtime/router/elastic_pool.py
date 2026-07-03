"""CP-45 — Elastic Compute Pool: unified node pool for AI-LAB.

Single source of truth for compute node selection, status, and fallback.
Wraps Dynamic Node Registry + Capability Scheduler + Multi-Node Routing
into one observable pool.

Node states:
  - online: healthy and accepting requests
  - offline: not reachable (excluded from routing)
  - degraded: reachable but under pressure (penalized)

Every decision is recorded with reason codes.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Cache TTL for node registry
_REGISTRY_TTL: float = 30.0
_last_registry_load: float = 0.0
_cached_registry: list[Any] | None = None


class ElasticComputePool:
    """Unified compute pool for AI-LAB runtime nodes.

    Usage:
        pool = ElasticComputePool()
        decision = pool.select(model="qwen2.5-14b", profile="chat")
        if decision["selected_node"]:
            url = decision["backend_url"]
    """

    def __init__(self, ttl: float = 30.0):
        self._ttl = ttl
        self._node_cache: dict[str, dict[str, Any]] = {}
        self._cache_time: float = 0.0
        # CP-46: pool observability counters
        self._selected_count: dict[str, int] = {}
        self._fallback_count: dict[str, int] = {}
        self._failure_count: dict[str, int] = {}
        self._last_selected_at: dict[str, float] = {}
        self._last_failure_at: dict[str, float] = {}
        self._last_fallback_at: dict[str, float] = {}
        self._total_selections = 0
        self._total_fallbacks = 0
        self._total_failures = 0

    # ── Registry loading ─────────────────────────────────────────────────

    def _load_registry(self) -> list[Any]:
        global _cached_registry, _last_registry_load
        now = time.time()
        if _cached_registry is not None and (now - _last_registry_load) < self._ttl:
            return _cached_registry
        try:
            from runtime.state.dynamic_node_registry import build_node_registry
            _cached_registry = build_node_registry()
            _last_registry_load = now
            return _cached_registry
        except Exception as exc:
            logger.warning("pool: cannot load node registry: %s", exc)
            return _cached_registry or []

    def _normalize_registry(self, registry: list[Any]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for entry in registry:
            if hasattr(entry, "node_id"):
                nodes.append({
                    "node_id": entry.node_id,
                    "hostname": getattr(entry, "hostname", ""),
                    "ip": getattr(entry, "ip", ""),
                    "role": getattr(entry, "role", "on_demand"),
                    "status": getattr(entry, "status", "unknown"),
                    "capabilities": list(getattr(entry, "capabilities", [])),
                    "models": [
                        {"id": m.id, "suitability": list(m.suitability)}
                        for m in getattr(entry, "models", [])
                    ],
                    "metrics": {
                        "latency_ms": getattr(getattr(entry, "metrics", None), "latency_ms", None),
                        "health_score": getattr(getattr(entry, "metrics", None), "health_score", 0.0),
                    },
                    "routing_eligible": getattr(entry, "routing_eligible", False),
                    "fallback_eligible": getattr(entry, "fallback_eligible", False),
                    "offline_is_failure": getattr(entry, "offline_is_failure", False),
                    "last_seen": getattr(entry, "last_seen", 0.0),
                    "evidence": list(getattr(entry, "evidence", [])),
                })
            elif isinstance(entry, dict):
                nodes.append(entry)
        return nodes

    # ── Node states ──────────────────────────────────────────────────────

    def get_online_nodes(self, registry: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if registry is None:
            registry = self.get_nodes()
        return [n for n in registry if n.get("status") == "online" and n.get("routing_eligible")]

    def get_offline_nodes(self, registry: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if registry is None:
            registry = self.get_nodes()
        return [n for n in registry if n.get("status") != "online" or not n.get("routing_eligible")]

    def get_degraded_nodes(self, registry: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if registry is None:
            registry = self.get_nodes()
        return [
            n for n in registry
            if n.get("status") == "online" and n.get("routing_eligible")
            and (n.get("metrics", {}).get("health_score", 1.0) < 0.5
                 or n.get("metrics", {}).get("latency_ms", 0) > 10000)
        ]

    def get_nodes(self) -> list[dict[str, Any]]:
        raw = self._load_registry()
        return self._normalize_registry(raw)

    # ── Capability extraction ──────────────────────────────────────────

    def _extract_capabilities(self, node: dict[str, Any]) -> set[str]:
        caps = set(node.get("capabilities", []))
        for m in node.get("models", []):
            if isinstance(m, dict):
                caps.update(m.get("suitability", []))
            elif hasattr(m, "suitability"):
                caps.update(m.suitability)
        return caps

    def _model_on_node(self, model_id: str, node: dict[str, Any]) -> bool:
        model_lower = model_id.lower()
        for m in node.get("models", []):
            mid = m.get("id", "") if isinstance(m, dict) else (m.id if hasattr(m, "id") else str(m))
            if mid.lower() == model_lower:
                return True
        return False

    # ── Node scoring ─────────────────────────────────────────────────

    def calculate_score(
        self,
        node: dict[str, Any],
        requirements: dict[str, Any],
        requested_model: str,
    ) -> dict[str, Any]:
        """Score a node's suitability for a request context.

        Returns:
            score, reasons[], breakdown{}, rejected bool, reject_reason,
            model_available, capability_match
        """
        node_id = node["node_id"]
        caps = self._extract_capabilities(node)
        model_on_node = self._model_on_node(requested_model, node)
        health = node.get("metrics", {}).get("health_score", 0.8)
        latency = node.get("metrics", {}).get("latency_ms", 0)

        score = 0.0
        reasons: list[str] = []
        breakdown: dict[str, float] = {}

        # 1. Model match (+4.0)
        if model_on_node:
            score += 4.0
            reasons.append("model_match")
            breakdown["model_match"] = 4.0

        # 2. Capability match (+3.0)
        cap_match = True
        for cap_key in ("vision", "coding", "reasoning", "large_context", "embedding"):
            if requirements.get(cap_key) and cap_key not in caps:
                cap_match = False
        if cap_match and any(requirements.get(k) for k in ("vision", "coding", "reasoning", "large_context", "embedding")):
            score += 3.0
            reasons.append("capability_match")
            breakdown["capability_match"] = 3.0

        # 3. rx7900xt requirement (hard gate)
        if requirements.get("requires_rx7900xt"):
            if "rx7900xt" not in node_id:
                return {
                    "score": 0.0, "reasons": ["rejected:model_only_on_rx7900xt"],
                    "breakdown": {}, "rejected": True,
                    "reject_reason": "model_only_on_rx7900xt",
                    "model_available": model_on_node, "capability_match": cap_match,
                }
            score += 5.0
            reasons.append("rx7900xt_required")
            breakdown["rx7900xt_required"] = 5.0

        # 4. Health (0-2.0)
        health_contrib = health * 2.0
        score += health_contrib
        breakdown["health"] = round(health_contrib, 2)
        if health >= 0.9:
            reasons.append("health_ok")
        elif health < 0.5:
            reasons.append("health_low")

        # 5. Degradation penalty (-2.0)
        is_degraded = (
            node.get("status") == "online" and node.get("routing_eligible")
            and (health < 0.5 or (latency and latency > 10000))
        )
        if is_degraded:
            score -= 2.0
            reasons.append("degraded_penalty")
            breakdown["degraded_penalty"] = -2.0

        # 6. Recent failures penalty (0 to -2.0)
        failures = self._failure_count.get(node_id, 0)
        if failures > 0:
            fpen = min(failures / 3.0, 2.0)
            score -= fpen
            reasons.append(f"failures({failures})")
            breakdown["failures_penalty"] = -round(fpen, 2)

        # 7. Recent fallbacks penalty (0 to -1.0)
        fallbacks = self._fallback_count.get(node_id, 0)
        if fallbacks > 0:
            fbpen = min(fallbacks / 5.0, 1.0)
            score -= fbpen
            reasons.append(f"fallbacks({fallbacks})")
            breakdown["fallbacks_penalty"] = -round(fbpen, 2)

        # 8. Recency penalty (recently selected = likely busy)
        last_sel = self._last_selected_at.get(node_id, 0.0)
        if last_sel > 0 and (time.time() - last_sel) < 30:
            score -= 0.5
            reasons.append("recency_penalty")
            breakdown["recency_penalty"] = -0.5

        # 9. Latency penalty
        if latency and latency > 5000:
            score -= 0.5
            reasons.append("high_latency")
            breakdown["latency_penalty"] = -0.5
        elif latency and latency > 2000:
            score -= 0.2
            reasons.append("elevated_latency")
            breakdown["latency_penalty"] = -0.2

        return {
            "score": round(score, 2),
            "reasons": reasons,
            "breakdown": breakdown,
            "rejected": False,
            "reject_reason": None,
            "model_available": model_on_node,
            "capability_match": cap_match,
        }

    # ── Capability requirement extraction ─────────────────────────────

    def extract_requirements(
        self,
        requested_model: str = "",
        profile: str = "",
        route_family: str = "",
        messages: list | None = None,
    ) -> dict[str, Any]:
        req: dict[str, Any] = {
            "vision": False, "coding": False, "reasoning": False,
            "large_context": False, "embedding": False,
            "requires_rx7900xt": False,
            "source": "none",
        }
        model_lower = requested_model.lower()
        if "moondream" in model_lower or "vision" in model_lower or "vl-" in model_lower:
            req["vision"] = True; req["source"] = "model_id"
        if any(p in model_lower for p in ("32b", "35b", "30b", "70b", "120b")):
            req["large_context"] = True; req["source"] = "model_id"
        if "coder" in model_lower or "code-" in model_lower:
            req["coding"] = True; req["source"] = "model_id"
        if "deepseek" in model_lower or "r1" in model_lower:
            req["reasoning"] = True; req["source"] = "model_id"
        if "embed" in model_lower:
            req["embedding"] = True; req["source"] = "model_id"
        rx7900xt_models = {
            "moondream2-20250414", "qwen3-coder-30b-a3b-instruct@q3_k_s",
            "qwen3-coder-30b-a3b-instruct@q4_k_xl", "qwen3.6-35b-a3b",
            "qwen/qwen3.6-35b-a3b", "openai_gpt-oss-20b",
            "qwen3.6-27b-claude-opus-reasoning-distilled",
            "text-embedding-nomic-embed-text-v2-moe",
            "gemma-4-12b-it", "qwen3.5-9b-deepseek-v4-flash-mtp",
        }
        if model_lower in rx7900xt_models:
            req["requires_rx7900xt"] = True; req["source"] = "model_id"
        profile_lower = profile.lower() if profile else ""
        if "coding" in profile_lower:
            if not req["vision"]: req["coding"] = True; req["source"] = "profile"
        if route_family == "reasoning":
            req["reasoning"] = True; req["source"] = "route_family"
        return req

    # ── Primary selection ──────────────────────────────────────────────

    def select(
        self,
        requested_model: str = "",
        profile: str = "",
        route_family: str = "",
        messages: list | None = None,
    ) -> dict[str, Any]:
        """Select the best node for a given request.

        Uses calculate_score() for multi-factor scoring.
        Returns:
            selected_node, backend_url, decision, confidence,
            reason_codes[], score_breakdown{}, fallback_candidates[]
        """
        registry = self.get_nodes()
        online = self.get_online_nodes(registry)
        requirements = self.extract_requirements(requested_model, profile, route_family, messages)

        if not online:
            return {
                "selected_node": "", "backend_url": "",
                "decision": "capacity_unavailable",
                "confidence": 1.0,
                "reason_codes": ["pool_no_online_nodes"],
                "fallback_candidates": [], "requirements": requirements,
            }

        scored = []
        for node in online:
            result = self.calculate_score(node, requirements, requested_model)
            url = self._get_url(node)
            scored.append({
                "node_id": node["node_id"],
                "url": url,
                **result,
            })

        eligible = [s for s in scored if not s.get("rejected")]
        eligible.sort(key=lambda s: s["score"], reverse=True)

        if not eligible:
            return {
                "selected_node": "", "backend_url": "",
                "decision": "capacity_unavailable",
                "confidence": 0.9,
                "reason_codes": ["pool_all_nodes_rejected"],
                "fallback_candidates": [], "requirements": requirements,
                "rejected_candidates": [s for s in scored if s.get("rejected")],
            }

        best = eligible[0]
        node_id = best["node_id"]
        self._selected_count[node_id] = self._selected_count.get(node_id, 0) + 1
        self._last_selected_at[node_id] = time.time()
        self._total_selections += 1
        return {
            "selected_node": best["node_id"],
            "backend_url": best["url"],
            "decision": "selected",
            "confidence": 0.95 if best.get("capability_match") and best.get("model_available") else 0.8,
            "reason_codes": ["pool_selected"] + best.get("reasons", []),
            "score_breakdown": best.get("breakdown", {}),
            "fallback_candidates": [{
                "node_id": c["node_id"],
                "url": c["url"],
                "score": c.get("score", 0.0),
                "reasons": c.get("reasons", []),
            } for c in eligible[1:]],
            "requirements": requirements,
        }

    # ── Fallback selection ────────────────────────────────────────────

    def fallback(
        self,
        requested_model: str,
        failed_node_id: str,
        failure_type: str = "backend_error",
    ) -> dict[str, Any] | None:
        """Select a fallback node when the primary node fails.

        Uses calculate_score() to pick the best available candidate.
        Prefers same-model nodes, then highest-scored.
        Returns fallback dict or None if no safe fallback exists.
        """
        registry = self.get_nodes()
        online = self.get_online_nodes(registry)

        candidates = [n for n in online if n["node_id"] != failed_node_id]
        if not candidates:
            return None

        requirements = self.extract_requirements(requested_model, "", "", [])
        scored = []
        for n in candidates:
            s = self.calculate_score(n, requirements, requested_model)
            if s.get("rejected"):
                continue
            url = self._get_url(n)
            scored.append({
                "node_id": n["node_id"], "url": url,
                **s,
            })

        if not scored:
            return None

        # Prefer same-model, then highest score
        scored.sort(key=lambda s: (-s.get("model_available", False), -s["score"]))
        best = scored[0]
        reason = "same_model_fallback" if best.get("model_available") else "scored_fallback"
        self._record_fallback(best["node_id"])
        return {
            "node_id": best["node_id"],
            "url": best["url"],
            "model": requested_model,
            "reason": reason,
            "fallback_score": best["score"],
            "fallback_reasons": best.get("reasons", []),
        }

    def _get_url(self, node: dict[str, Any]) -> str:
        try:
            from runtime.router.multi_node_routing import BACKEND_URLS
            return BACKEND_URLS.get(node["node_id"], f"http://{node['ip']}:1234/v1")
        except Exception:
            return f"http://{node['ip']}:1234/v1"

    # ── Observability ──────────────────────────────────────────────────

    def _record_fallback(self, node_id: str) -> None:
        self._fallback_count[node_id] = self._fallback_count.get(node_id, 0) + 1
        self._last_fallback_at[node_id] = time.time()
        self._total_fallbacks += 1

    def record_failure(self, node_id: str, failure_type: str = "backend_error") -> None:
        self._failure_count[node_id] = self._failure_count.get(node_id, 0) + 1
        self._last_failure_at[node_id] = time.time()
        self._total_failures += 1

    def get_metrics(self) -> dict[str, Any]:
        all_nodes: set[str] = set()
        all_nodes.update(self._selected_count.keys())
        all_nodes.update(self._fallback_count.keys())
        all_nodes.update(self._failure_count.keys())
        return {
            "pool": "elastic-compute-pool-01",
            "contract_version": "CP-47-NODE-SCORING-01",
            "timestamp": time.time(),
            "total_selections": self._total_selections,
            "total_fallbacks": self._total_fallbacks,
            "total_failures": self._total_failures,
            "per_node": {
                nid: {
                    "selected_count": self._selected_count.get(nid, 0),
                    "fallback_count": self._fallback_count.get(nid, 0),
                    "failure_count": self._failure_count.get(nid, 0),
                    "last_selected_at": self._last_selected_at.get(nid, 0.0),
                    "last_failure_at": self._last_failure_at.get(nid, 0.0),
                    "last_fallback_at": self._last_fallback_at.get(nid, 0.0),
                }
                for nid in sorted(all_nodes)
            },
            "scoring_version": "CP-47-NODE-SCORING-01",
        }

    # ── Pool status ───────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        registry = self.get_nodes()
        online = self.get_online_nodes(registry)
        offline = self.get_offline_nodes(registry)
        degraded = self.get_degraded_nodes(registry)

        nodes_by_role: dict[str, list[dict]] = {}
        for n in registry:
            role = n.get("role", "unknown")
            nodes_by_role.setdefault(role, []).append({
                "node_id": n["node_id"],
                "hostname": n.get("hostname", ""),
                "ip": n.get("ip", ""),
                "status": n.get("status", "unknown"),
                "capabilities": list(n.get("capabilities", [])),
                "model_count": len(n.get("models", [])),
                "health_score": n.get("metrics", {}).get("health_score", 0.0),
                "routing_eligible": n.get("routing_eligible", False),
            })

        return {
            "pool": "elastic-compute-pool-01",
            "contract_version": "CP-47-NODE-SCORING-01",
            "timestamp": time.time(),
            "nodes_total": len(registry),
            "nodes_online": len(online),
            "nodes_offline": len(offline),
            "nodes_degraded": len(degraded),
            "required_offline_critical": any(
                n.get("offline_is_failure") for n in registry if n.get("status") != "online"
            ),
            "nodes_by_role": nodes_by_role,
            "nodes": [{
                "node_id": n["node_id"],
                "status": n.get("status", "unknown"),
                "hostname": n.get("hostname", ""),
                "ip": n.get("ip", ""),
                "role": n.get("role", "unknown"),
                "capabilities": list(n.get("capabilities", [])),
                "model_count": len(n.get("models", [])),
                "health_score": n.get("metrics", {}).get("health_score", 0.0),
                "routing_eligible": n.get("routing_eligible", False),
                "degraded": n["node_id"] in {d["node_id"] for d in degraded},
                "score": self.calculate_score(n, {
                    "vision": False, "coding": False, "reasoning": False,
                    "large_context": False, "embedding": False,
                    "requires_rx7900xt": False, "source": "none",
                }, "").get("score", 0.0),
            } for n in registry],
        }

    def get_summary(self) -> dict[str, Any]:
        status = self.get_status()
        return {
            "pool": status["pool"],
            "timestamp": status["timestamp"],
            "nodes_total": status["nodes_total"],
            "nodes_online": status["nodes_online"],
            "nodes_offline": status["nodes_offline"],
            "nodes_degraded": status["nodes_degraded"],
            "required_offline_critical": status["required_offline_critical"],
            "metrics_summary": {
                "total_selections": self._total_selections,
                "total_fallbacks": self._total_fallbacks,
                "total_failures": self._total_failures,
            },
        }


# ── Module-level singleton ────────────────────────────────────────────────

_pool: ElasticComputePool | None = None


def get_pool() -> ElasticComputePool:
    global _pool
    if _pool is None:
        _pool = ElasticComputePool()
    return _pool


def select_node(
    requested_model: str = "",
    profile: str = "",
    route_family: str = "",
    messages: list | None = None,
) -> dict[str, Any]:
    """Convenience: select node from pool."""
    return get_pool().select(requested_model, profile, route_family, messages)


def get_pool_status() -> dict[str, Any]:
    return get_pool().get_status()


def get_pool_summary() -> dict[str, Any]:
    return get_pool().get_summary()


def get_pool_metrics() -> dict[str, Any]:
    return get_pool().get_metrics()


def get_prometheus_metrics() -> str:
    """Export pool metrics in Prometheus text/plain format."""
    pool = get_pool()
    status = pool.get_status()
    summary = pool.get_summary()
    m = pool.get_metrics()

    lines: list[str] = []

    def _g(name: str, help_text: str, value_type: str = "gauge"):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {value_type}")

    def _val(name: str, value, **labels):
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            lines.append(f"{name}{{{label_str}}} {value}")
        else:
            lines.append(f"{name} {value}")

    # Pool totals
    _g("ailab_pool_nodes_total", "Total nodes in pool")
    _val("ailab_pool_nodes_total", status["nodes_total"], contract_version="CP-48A")
    _g("ailab_pool_nodes_online", "Online nodes")
    _val("ailab_pool_nodes_online", status["nodes_online"])
    _g("ailab_pool_nodes_degraded", "Degraded nodes")
    _val("ailab_pool_nodes_degraded", status["nodes_degraded"])
    _g("ailab_pool_nodes_offline", "Offline nodes")
    _val("ailab_pool_nodes_offline", status["nodes_offline"])

    # Event counters (TYPE counter, _total suffix)
    _g("ailab_pool_selections_total", "Total node selections", "counter")
    _val("ailab_pool_selections_total", m["total_selections"])
    _g("ailab_pool_fallbacks_total", "Total fallback selections", "counter")
    _val("ailab_pool_fallbacks_total", m["total_fallbacks"])
    _g("ailab_pool_failures_total", "Total backend failures recorded", "counter")
    _val("ailab_pool_failures_total", m["total_failures"])

    # Per-node metrics
    for node_entry in status.get("nodes", []):
        nid = node_entry["node_id"]
        pn = m.get("per_node", {}).get(nid, {})
        base_score = node_entry.get("score", 0.0)
        on = 1 if node_entry.get("status") == "online" and node_entry.get("routing_eligible") else 0
        dg = 1 if node_entry.get("degraded", False) else 0
        caps = ",".join(sorted(node_entry.get("capabilities", [])))

        _g("ailab_pool_node_score", "Current baseline node score")
        _val("ailab_pool_node_score", base_score, node=nid, capabilities=caps)

        _g("ailab_pool_node_selected_total", "Total selections for this node", "counter")
        _val("ailab_pool_node_selected_total", pn.get("selected_count", 0), node=nid)

        _g("ailab_pool_node_fallback_total", "Total fallbacks to this node", "counter")
        _val("ailab_pool_node_fallback_total", pn.get("fallback_count", 0), node=nid)

        _g("ailab_pool_node_failure_total", "Total failures on this node", "counter")
        _val("ailab_pool_node_failure_total", pn.get("failure_count", 0), node=nid)

        _g("ailab_pool_node_online", "Whether the node is online (1/0)")
        _val("ailab_pool_node_online", on, node=nid)

        _g("ailab_pool_node_degraded", "Whether the node is degraded (1/0)")
        _val("ailab_pool_node_degraded", dg, node=nid)

    return "\n".join(lines) + "\n"
