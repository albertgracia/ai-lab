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

        Returns:
            selected_node, backend_url, decision, confidence,
            reason_codes[], fallback_candidates[]
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

        # Score each online node
        scored = []
        for node in online:
            caps = self._extract_capabilities(node)
            model_on_node = self._model_on_node(requested_model, node)
            health = node.get("metrics", {}).get("health_score", 0.8)

            score = 0.0
            reasons = []

            # Model match
            if model_on_node:
                score += 4.0
                reasons.append("model_on_node")

            # Capability match
            cap_match = True
            for cap_key in ("vision", "coding", "reasoning", "large_context", "embedding"):
                if requirements.get(cap_key) and cap_key not in caps:
                    cap_match = False
            if cap_match and any(requirements.get(k) for k in ("vision", "coding", "reasoning", "large_context", "embedding")):
                score += 3.0
                reasons.append("capability_match")

            # rx7900xt requirement
            if requirements.get("requires_rx7900xt"):
                if "rx7900xt" not in node["node_id"]:
                    reasons.append("rejected: model_only_on_rx7900xt")
                    scored.append({
                        "node_id": node["node_id"],
                        "url": node.get("ip", ""),
                        "score": 0.0,
                        "model_available": model_on_node,
                        "capability_match": cap_match,
                        "reasons": reasons,
                        "rejected": True,
                        "reject_reason": "model_only_on_rx7900xt",
                    })
                    continue
                score += 5.0
                reasons.append("rx7900xt_required")

            # Health
            score += health * 2.0
            if health >= 0.9:
                reasons.append("health_ok")
            elif health < 0.5:
                reasons.append("health_degraded")

            # URL
            try:
                from runtime.router.multi_node_routing import BACKEND_URLS
                url = BACKEND_URLS.get(node["node_id"], f"http://{node['ip']}:1234/v1")
            except Exception:
                url = f"http://{node['ip']}:1234/v1"

            scored.append({
                "node_id": node["node_id"],
                "url": url,
                "score": round(score, 2),
                "model_available": model_on_node,
                "capability_match": cap_match,
                "reasons": reasons,
                "rejected": False,
            })

        # Sort by score descending
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
            "fallback_candidates": eligible[1:],
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

        Returns fallback dict or None if no safe fallback exists.
        """
        registry = self.get_nodes()
        online = self.get_online_nodes(registry)

        # Exclude failed node
        candidates = [n for n in online if n["node_id"] != failed_node_id]
        if not candidates:
            return None

        # Prefer same model, then capability match
        model_lower = requested_model.lower()
        requires_vision = "moondream" in model_lower or "vision" in model_lower
        requires_large = any(p in model_lower for p in ("32b", "35b", "30b"))

        for candidate in candidates:
            # Same model available?
            if self._model_on_node(requested_model, candidate):
                url = self._get_url(candidate)
                self._record_fallback(candidate["node_id"])
                return {"node_id": candidate["node_id"], "url": url,
                        "model": requested_model, "reason": "same_model_fallback"}

            # Capability match for vision/large?
            caps = self._extract_capabilities(candidate)
            if requires_vision and "vision" in caps:
                url = self._get_url(candidate)
                self._record_fallback(candidate["node_id"])
                return {"node_id": candidate["node_id"], "url": url,
                        "model": requested_model, "reason": "vision_capability_fallback"}
            if requires_large and "large-context" in caps:
                url = self._get_url(candidate)
                self._record_fallback(candidate["node_id"])
                return {"node_id": candidate["node_id"], "url": url,
                        "model": requested_model, "reason": "large_context_fallback"}

        # Last resort: any online node
        if candidates:
            c = candidates[0]
            url = self._get_url(c)
            self._record_fallback(c["node_id"])
            return {"node_id": c["node_id"], "url": url,
                    "model": requested_model, "reason": "any_online_fallback"}

        return None

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
            "contract_version": "CP-46-POOL-OBSERVABILITY-01",
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
            "contract_version": "CP-45-ELASTIC-COMPUTE-POOL-01",
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
