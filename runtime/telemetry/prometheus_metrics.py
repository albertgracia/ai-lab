"""Prometheus metrics exposed via prometheus_client.

Counters, gauges, and histograms for AI-LAB governance and observability.
Uses the official prometheus_client library (already in venv).
"""

from prometheus_client import Counter, Gauge, Histogram

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

EMBEDDING_INPUT_CHARS = Gauge(
    "ailab_embedding_input_chars",
    "Caracteres del ultimo texto enviado al pipeline de embeddings",
)

EMBEDDING_TRUNCATIONS = Counter(
    "ailab_embedding_truncations_total",
    "Numero total de entradas de embeddings truncadas por exceso de longitud",
)

RECALL_QUERY_CHARS = Gauge(
    "ailab_recall_query_chars",
    "Caracteres del ultimo texto usado en recall semantico",
)

ROUTE_FAMILY_TOTAL = Counter(
    "ailab_route_family_total",
    "Numero total de solicitudes clasificadas por familia de ruta",
    ["family"],
)

ROUTE_FAMILY_LATENCY = Histogram(
    "ailab_route_family_latency_ms",
    "Latencia por familia de ruta en milisegundos",
    ["family"],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000),
)

ROUTE_FAMILY_PROMPT_TOKENS = Counter(
    "ailab_route_family_prompt_tokens_total",
    "Tokens de prompt acumulados por familia de ruta",
    ["family"],
)

ROUTE_FAMILY_COMPLETION_TOKENS = Counter(
    "ailab_route_family_completion_tokens_total",
    "Tokens de completion acumulados por familia de ruta",
    ["family"],
)

ROUTE_FAMILY_ERRORS = Counter(
    "ailab_route_family_errors_total",
    "Errores acumulados por familia de ruta",
    ["family"],
)

ROUTE_FAMILY_BLOCKED = Counter(
    "ailab_route_family_blocked_total",
    "Bloqueos de policy acumulados por familia de ruta",
    ["family"],
)

PROFILE_TOTAL = Counter(
    "ailab_profile_total",
    "Peticiones por perfil cognitivo, ruta y modelo",
    ["profile", "route_family", "model"],
)

DEFAULT_ROUTE_FAMILIES = (
    "minimal",
    "observe",
    "tool_fastpath",
    "cognitive",
    "learning",
)


def record_route_family_metrics(
    family: str,
    *,
    count: bool = True,
    latency_ms: float | int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    error: bool = False,
    blocked: bool = False,
) -> None:
    fam = family or "unknown"
    if count:
        ROUTE_FAMILY_TOTAL.labels(family=fam).inc()
    if latency_ms is not None:
        ROUTE_FAMILY_LATENCY.labels(family=fam).observe(float(latency_ms))
    if prompt_tokens is not None and prompt_tokens >= 0:
        ROUTE_FAMILY_PROMPT_TOKENS.labels(family=fam).inc(prompt_tokens)
    if completion_tokens is not None and completion_tokens >= 0:
        ROUTE_FAMILY_COMPLETION_TOKENS.labels(family=fam).inc(completion_tokens)
    if error:
        ROUTE_FAMILY_ERRORS.labels(family=fam).inc()
    if blocked:
        ROUTE_FAMILY_BLOCKED.labels(family=fam).inc()


def record_profile_metrics(profile: str, route_family: str, model: str) -> None:
    PROFILE_TOTAL.labels(profile=profile, route_family=route_family, model=model or "unknown").inc()


def prime_profile_metrics(profiles: tuple[str, ...] = ("chat", "coding", "analysis", "observe", "agent")) -> None:
    for prof in profiles:
        PROFILE_TOTAL.labels(profile=prof, route_family="primed", model="none").inc(0)


def prime_route_family_metrics(families: tuple[str, ...] = DEFAULT_ROUTE_FAMILIES) -> None:
    """Create zero-valued labeled series so Grafana shows 0 instead of no data."""
    for fam in families:
        ROUTE_FAMILY_TOTAL.labels(family=fam).inc(0)
        ROUTE_FAMILY_PROMPT_TOKENS.labels(family=fam).inc(0)
        ROUTE_FAMILY_COMPLETION_TOKENS.labels(family=fam).inc(0)
        ROUTE_FAMILY_ERRORS.labels(family=fam).inc(0)
        ROUTE_FAMILY_BLOCKED.labels(family=fam).inc(0)
