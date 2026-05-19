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

TOOL_CALL_TOTAL = Counter(
    "ailab_tool_call_total",
    "Tool calls procesadas por nombre, resultado y politica",
    ["tool_name", "result", "policy", "mode"],
)

MEMORY_RECALL_TOTAL = Counter(
    "ailab_memory_recall_total",
    "Ejecuciones de recall por politica y si hubo hit",
    ["policy", "hit"],
)
MEMORY_CHARS_INJECTED = Histogram(
    "ailab_memory_chars_injected",
    "Caracteres inyectados por recall",
    ["policy"],
    buckets=(100, 250, 500, 800, 1200, 2000, 4000, 8000),
)
MEMORY_ITEMS_TOTAL = Counter(
    "ailab_memory_items_total",
    "Items de memoria recuperados por politica y fuente",
    ["policy", "source"],
)

MEMORY_CONTAMINATION = Histogram(
    "ailab_memory_contamination_risk",
    "Riesgo de contaminacion del recall (proporcion de items con score < 0.15)",
    ["policy"],
    buckets=(0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.8),
)
MEMORY_QUALITY_SCORE = Histogram(
    "ailab_memory_quality_score",
    "Puntuacion media de calidad del recall",
    ["policy"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9),
)

CONTEXT_CAP_EXCEEDED = Counter(
    "ailab_context_cap_exceeded_total",
    "Veces que el contexto total excedio el hard cap por politica (shadow mode)",
    ["policy"],
)

TOOL_EMPTY_ARGUMENTS = Counter(
    "ailab_tool_empty_arguments_total",
    "Bash tools bloqueadas por arguments vacios",
)
TOOL_QUESTION_STRIPPED = Counter(
    "ailab_tool_question_stripped_total",
    "Veces que se elimino la question tool del payload",
)
CONFIRMATION_REQUIRED = Counter(
    "ailab_confirmation_required_total",
    "Veces que se requirio confirmacion (428) para write tools",
)

COMPLETION_TRUNCATED = Counter(
    "ailab_completion_truncated_total",
    "Completions truncadas con contenido valido (finish_reason=length)",
    ["route_family"],
)
COMPLETION_EMPTY_AFTER_TRUNCATION = Counter(
    "ailab_completion_empty_after_truncation_total",
    "Completions truncadas y vacias (finish_reason=length, sin contenido)",
)

REPORT_REQUESTS_BY_MODEL = Counter(
    "ailab_report_requests_by_model_total",
    "Peticiones de informe por modelo y tipo (heavy/light)",
    ["model", "type"],
)

CAPABILITY_ANSWERS_TOTAL = Counter(
    "ailab_capability_answers_total",
    "Respuestas de capacidad (que-puedes-hacer) sin pasar por LM Studio",
)
CREATIVE_REQUESTS_TOTAL = Counter(
    "ailab_creative_requests_total",
    "Peticiones de escritura creativa/longform",
)

# ── FASE 27.1: latency & throughput ──────────────────────────────
FIRST_TOKEN_LATENCY = Histogram(
    "ailab_first_token_latency_ms",
    "Tiempo hasta el primer token (TTFB)",
    ["model"],
    buckets=(50, 100, 250, 500, 1000, 2000, 5000, 10000, 30000),
)
REQUEST_TOTAL_LATENCY = Histogram(
    "ailab_request_total_latency_ms",
    "Latencia total de request (end-to-end)",
    ["route_family"],
    buckets=(50, 100, 250, 500, 1000, 2000, 5000, 10000, 30000),
)
COMPLETION_STREAM_DURATION = Histogram(
    "ailab_completion_stream_duration_ms",
    "Duracion del stream de completion (ultimo chunk - primer token)",
    ["model"],
    buckets=(100, 500, 1000, 2000, 5000, 10000, 20000, 60000),
)
COLD_START_TOTAL = Counter(
    "ailab_cold_start_total",
    "Cold starts detectados (modelo no estaba en memoria)",
    ["model"],
)
GPU_ACTIVE_REQUESTS = Gauge(
    "ailab_gpu_active_requests",
    "Requests activas en GPU (estimado por requests en vuelo)",
)
GPU_ESTIMATED_UTILIZATION = Gauge(
    "ailab_gpu_estimated_utilization_pct",
    "Utilizacion GPU estimada (requests activas / capacidad concurrente)",
)

# ── FASE 27.1.1: streaming stabilization ─────────────────────────
STREAM_CHUNKS_TOTAL = Counter(
    "ailab_stream_chunks_total",
    "Chunks SSE emitidos",
)
STREAM_EMPTY_CHUNKS = Counter(
    "ailab_stream_empty_chunks_total",
    "Chunks SSE vacios",
)
STREAM_STALLS = Counter(
    "ailab_stream_stalls_total",
    "Stalls de stream (>5s entre chunks)",
)
STREAM_FINISH_INCONSISTENT = Counter(
    "ailab_stream_finish_inconsistent_total",
    "finish_reason inconsistente en stream",
)

# ── FASE 27.5: prompt governance ─────────────────────────────────
PROMPT_CHECKSUM_CHANGES = Counter(
    "ailab_prompt_checksum_changes_total",
    "Cambios detectados en prompts versionados",
    ["prompt_name"],
)

# ── FASE 27.3: quality guard ─────────────────────────────────────
QUALITY_SCORE = Histogram(
    "ailab_quality_score",
    "Puntuacion de calidad de respuesta",
    ["route_family"],
    buckets=(0, 25, 50, 75, 100),
)
HALLUCINATION_RISK = Histogram(
    "ailab_hallucination_risk",
    "Riesgo de alucinacion estimado",
    ["route_family"],
    buckets=(0, 10, 20, 50, 100),
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


def record_tool_call_metric(tool_name: str, result: str, policy: str, mode: str) -> None:
    TOOL_CALL_TOTAL.labels(tool_name=tool_name or "unknown", result=result, policy=policy or "unknown", mode=mode or "unknown").inc()


def record_memory_metrics(ctx: dict, policy_name: str) -> None:
    hit = "true" if ctx.get("memories", 0) > 0 else "false"
    MEMORY_RECALL_TOTAL.labels(policy=policy_name or "unknown", hit=hit).inc()
    if not ctx.get("skipped", True):
        MEMORY_CHARS_INJECTED.labels(policy=policy_name or "unknown").observe(float(ctx.get("chars", 0)))
    for source in ctx.get("sources", []) or []:
        MEMORY_ITEMS_TOTAL.labels(policy=policy_name or "unknown", source=source).inc()


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
