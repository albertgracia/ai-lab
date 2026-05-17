"""Prometheus metrics exposed via prometheus_client.

Counters and gauges for AI-LAB governance and observability.
Uses the official prometheus_client library (already in venv).
"""

from prometheus_client import Counter, Gauge

HARD_FACTS_HITS = Counter(
    "ailab_router_hard_facts_hits_total",
    "Numero total de peticiones que activaron el modo determinista Hard Facts",
)

ROUTER_REQUESTS = Counter(
    "ailab_router_chat_requests_total",
    "Numero total de peticiones al endpoint /v1/chat/completions del router",
)

GOVERNANCE_BLOCKED = Counter(
    "ailab_governance_blocked_actions_total",
    "Numero total de comandos destructivos interceptados y bloqueados",
)

GOVERNANCE_BLOCKED_BY_REASON = Counter(
    "ailab_governance_blocked_actions_by_reason_total",
    "Bloqueos desglosados por tipo de comando peligroso detectado",
    ["reason"],
)
