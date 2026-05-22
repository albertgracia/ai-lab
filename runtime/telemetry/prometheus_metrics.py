"""Prometheus metrics exposed via prometheus_client.

Counters, gauges, and histograms for AI-LAB governance and observability.
Uses the official prometheus_client library (already in venv).
"""

import time
from typing import Any

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
TOOL_PARALLEL_BLOCKED = Counter(
    "ailab_tool_parallel_call_blocked_total",
    "Parallel tool calls blocked — model only supports single calls",
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
    ["model", "route_family", "profile"],
)
COMPLETION_EMPTY_AFTER_TRUNCATION = Counter(
    "ailab_completion_empty_after_truncation_total",
    "Completions truncadas y vacias (finish_reason=length, sin contenido)",
)
EMPTY_RESPONSE_PREVENTED = Counter(
    "ailab_empty_response_prevented_total",
    "Respuestas vacias evitadas con contenido de respaldo",
    ["reason"],
)

REPORT_REQUESTS_BY_MODEL = Counter(
    "ailab_report_requests_by_model_total",
    "Peticiones de informe por modelo y tipo (heavy/light)",
    ["model", "type"],
)


def record_report_request(model: str, report_type: str) -> None:
    REPORT_REQUESTS_BY_MODEL.labels(model=model or "unknown", type=report_type or "unknown").inc()

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

# ── FASE 28.0: Agentic Runtime Metrics ──────────────────────
AGENTIC_PLANS_TOTAL = Counter(
    "ailab_agentic_plans_total",
    "Planes agentic generados",
    ["route_family", "intent_count"],
)
AGENTIC_DRY_RUNS_TOTAL = Counter(
    "ailab_agentic_dry_runs_total",
    "Dry-runs completados",
    ["risk_level"],
)
AGENTIC_RISK_SCORE = Histogram(
    "ailab_agentic_risk_score",
    "Puntuacion de riesgo agentic (0-3)",
    ["route_family"],
    buckets=(0, 1, 2, 3, 4),
)
AGENTIC_APPROVALS_REQUESTED = Counter(
    "ailab_agentic_approvals_requested_total",
    "Aprobaciones solicitadas",
    ["approval_type"],
)
AGENTIC_APPROVALS_GRANTED = Counter(
    "ailab_agentic_approvals_granted_total",
    "Aprobaciones concedidas",
    [],
)
AGENTIC_APPROVALS_REJECTED = Counter(
    "ailab_agentic_approvals_rejected_total",
    "Aprobaciones rechazadas",
    [],
)
AGENTIC_APPROVALS_EXPIRED = Counter(
    "ailab_agentic_approvals_expired_total",
    "Aprobaciones expiradas por TTL",
    [],
)
AGENTIC_EXECUTIONS_TOTAL = Counter(
    "ailab_agentic_executions_total",
    "Ejecuciones completadas",
    ["result", "execution_mode"],
)
AGENTIC_ACTIONS_TOTAL = Counter(
    "ailab_agentic_actions_total",
    "Acciones individuales ejecutadas",
    ["tool", "result", "intent"],
)
AGENTIC_EXECUTION_DURATION = Histogram(
    "ailab_agentic_execution_duration_ms",
    "Duracion total de ejecucion agentic",
    ["phase"],
    buckets=(100, 500, 1000, 5000, 15000, 30000, 60000),
)
AGENTIC_ROLLBACKS_TOTAL = Counter(
    "ailab_agentic_rollbacks_total",
    "Rollbacks ejecutados",
    ["reason"],
)
AGENTIC_GOVERNANCE_BLOCKS = Counter(
    "ailab_agentic_governance_blocks_total",
    "Acciones bloqueadas por governance agentic",
    ["reason"],
)

# ── FASE 28.0-C: Extended governance metrics ──
AGENTIC_STUCK_WORKFLOWS = Counter(
    "ailab_agentic_stuck_workflows_total",
    "Workflows atascados en un estado",
    ["state"],
)
AGENTIC_WORKFLOW_RETRIES = Counter(
    "ailab_agentic_workflow_retries_total",
    "Reintentos de workflow",
    ["reason"],
)
AGENTIC_WORKFLOW_CANCELLATIONS = Counter(
    "ailab_agentic_workflow_cancellations_total",
    "Cancelaciones de workflow",
    ["reason"],
)
AGENTIC_REPLAY_HASH_MISMATCH = Counter(
    "ailab_agentic_replay_hash_mismatch_total",
    "Mismatches de hash en replay",
    ["field"],
)

# ── FASE 29.0: Gateway Lifecycle Metrics ────────────────────
GATEWAY_UPTIME = Gauge(
    "ailab_gateway_uptime_seconds",
    "Gateway uptime in seconds",
)
GATEWAY_BOOT_TOTAL = Counter(
    "ailab_gateway_boot_total",
    "Gateway starts (boot count)",
)
GATEWAY_CLEAN_SHUTDOWN = Counter(
    "ailab_gateway_clean_shutdown_total",
    "Clean shutdowns (SIGTERM handled)",
)
GATEWAY_UNCLEAN_SHUTDOWN = Counter(
    "ailab_gateway_unclean_shutdown_total",
    "Unclean shutdowns (crash/kill)",
)
GATEWAY_SINGLETON_VIOLATION = Counter(
    "ailab_gateway_singleton_violation_total",
    "Singleton lock violations",
)
GATEWAY_PORT_CONFLICT = Counter(
    "ailab_port_conflict_total",
    "Port ownership conflicts detected",
)
GATEWAY_THREADS = Gauge(
    "ailab_gateway_threads",
    "Active thread count in gateway",
)

# ── FASE 29.3: Model Set Simplification Metrics ─────────────
DISABLED_MODEL_SELECTION = Counter(
    "ailab_disabled_model_selection_total",
    "Redirecciones de modelos desactivados",
    ["model", "reason"],
)

# ── FASE 29.3.1: Routing Tightening Metrics ──────────────────
GREETING_FASTPATH_TOTAL = Counter(
    "ailab_greeting_fastpath_total",
    "Greetings routed via fastpath to llama",
    [],
)
QWEN_ESCALATION_TOTAL = Counter(
    "ailab_qwen_escalation_total",
    "Qwen14b activations by escalation reason",
    ["reason"],
)
LLAMA_FASTPATH_TOTAL = Counter(
    "ailab_llama_fastpath_total",
    "Lightweight prompts routed to llama",
    [],
)

# ── FASE 29.0: Residency Metrics ────────────────────────────
RESIDENCY_HITS = Counter(
    "ailab_residency_hits_total",
    "Model was already loaded in VRAM",
    ["model"],
)
RESIDENCY_MISSES = Counter(
    "ailab_residency_misses_total",
    "Model needed loading (cold start or unloaded)",
    ["model"],
)
MODEL_LOAD_SECONDS = Histogram(
    "ailab_model_load_seconds",
    "Time to load model into VRAM",
    ["model"],
    buckets=(1, 5, 10, 30, 60, 120, 300),
)
QUEUE_WAIT_SECONDS = Histogram(
    "ailab_queue_wait_seconds",
    "Time waiting for GPU slot",
    ["model"],
    buckets=(0.1, 0.5, 1, 5, 10, 30, 60),
)
TOKENS_PER_SECOND = Gauge(
    "ailab_tokens_per_second",
    "Estimated tokens per second throughput",
    ["model"],
)

# ── FASE 28.1: Planner Runtime Skeleton Metrics ──────────────
PLANNER_PLANS_TOTAL = Counter(
    "ailab_planner_plans_total",
    "Planes readonly generados por el planner",
    ["plan_type"],
)
PLANNER_DAG_NODES_TOTAL = Histogram(
    "ailab_planner_dag_nodes_total",
    "Numero de nodos en DAG generados",
    ["plan_type"],
    buckets=(1, 2, 3, 4, 5, 6, 7, 8),
)
PLANNER_BLOCKED_TOTAL = Counter(
    "ailab_planner_blocked_total",
    "Planes bloqueados por governance",
    ["blocked_reason"],
)
PLANNER_PERMISSION_SCOPE_TOTAL = Counter(
    "ailab_planner_permission_scope_total",
    "Distribucion de permission scopes en planes",
    ["scope"],
)
PLANNER_VALIDATION_FAILURES_TOTAL = Counter(
    "ailab_planner_validation_failures_total",
    "Fallos de validacion en planes generados",
    ["reason"],
)

# ── FASE 29.0: Streaming Metrics (preparatory) ──────────────
STREAM_FIRST_CHUNK_LATENCY = Histogram(
    "ailab_stream_first_chunk_ms",
    "Latency to first SSE chunk",
    ["model"],
    buckets=(50, 100, 250, 500, 1000, 5000, 15000, 30000),
)
STREAM_CHUNK_CADENCE = Histogram(
    "ailab_stream_chunk_cadence_ms",
    "Time between consecutive SSE chunks",
    ["model"],
    buckets=(10, 50, 100, 250, 500, 1000),
)
STREAM_FINALIZATION_MISMATCH = Counter(
    "ailab_stream_finalization_mismatch_total",
    "finish_reason inconsistent with content end",
    [],
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


# ── FASE 28.0: Agentic metric recorders ──────────────────────

def record_agentic_plan(route_family: str, intent_count: int) -> None:
    AGENTIC_PLANS_TOTAL.labels(route_family=route_family, intent_count=str(intent_count)).inc()


def record_agentic_dry_run(risk_level: str) -> None:
    AGENTIC_DRY_RUNS_TOTAL.labels(risk_level=risk_level).inc()


def record_agentic_risk_score(route_family: str, score: int) -> None:
    AGENTIC_RISK_SCORE.labels(route_family=route_family).observe(float(score))


def record_agentic_approval_requested(approval_type: str) -> None:
    AGENTIC_APPROVALS_REQUESTED.labels(approval_type=approval_type).inc()


def record_agentic_approval_granted() -> None:
    AGENTIC_APPROVALS_GRANTED.inc()


def record_agentic_approval_rejected() -> None:
    AGENTIC_APPROVALS_REJECTED.inc()


def record_agentic_approval_expired() -> None:
    AGENTIC_APPROVALS_EXPIRED.inc()


def record_agentic_execution(result: str, execution_mode: str) -> None:
    AGENTIC_EXECUTIONS_TOTAL.labels(result=result, execution_mode=execution_mode).inc()


def record_agentic_action(tool: str, result: str, intent: str) -> None:
    AGENTIC_ACTIONS_TOTAL.labels(tool=tool, result=result, intent=intent).inc()


def record_agentic_execution_duration(phase: str, duration_ms: int) -> None:
    AGENTIC_EXECUTION_DURATION.labels(phase=phase).observe(float(duration_ms))


def record_agentic_rollback(reason: str) -> None:
    AGENTIC_ROLLBACKS_TOTAL.labels(reason=reason).inc()


def record_agentic_governance_block(reason: str) -> None:
    AGENTIC_GOVERNANCE_BLOCKS.labels(reason=reason).inc()


# ── FASE 28.0-C: Extended metrics recorders ──

def record_agentic_stuck_workflow(state: str) -> None:
    AGENTIC_STUCK_WORKFLOWS.labels(state=state).inc()


def record_agentic_workflow_retry(reason: str) -> None:
    AGENTIC_WORKFLOW_RETRIES.labels(reason=reason).inc()


def record_agentic_workflow_cancellation(reason: str) -> None:
    AGENTIC_WORKFLOW_CANCELLATIONS.labels(reason=reason).inc()


def record_agentic_replay_hash_mismatch(field: str) -> None:
    AGENTIC_REPLAY_HASH_MISMATCH.labels(field=field).inc()


# ── FASE 29.3: Model Set Simplification Recorders ───

def record_disabled_model_selection(model: str, reason: str) -> None:
    DISABLED_MODEL_SELECTION.labels(model=model, reason=reason).inc()


# ── FASE 29.4.1: Report Runtime Grounding Metrics ────────────
REPORT_GROUNDING_TOTAL = Counter(
    "ailab_report_grounding_total",
    "Report requests with OBSERVED_RUNTIME injected",
    [],
)
REPORT_MISSING_FIELDS_TOTAL = Counter(
    "ailab_report_missing_fields_total",
    "Report requests with missing fields",
    ["count"],
)
REPORT_TARGET_IP_TOTAL = Counter(
    "ailab_report_target_ip_total",
    "Report requests with detected target IP/domain",
    [],
)
REPORT_UNGROUNDED_TOTAL = Counter(
    "ailab_report_ungrounded_total",
    "Report requests with zero observed fields",
    [],
)

# ── FASE 29.4.3: Runtime Identity Grounding Metrics ────────────
REPORT_RUNTIME_IDENTITY_MATCH = Counter(
    "ailab_report_runtime_identity_match_total",
    "Report requests where target IP matches primary runtime IP",
    [],
)
REPORT_RUNTIME_IDENTITY_MISMATCH = Counter(
    "ailab_report_runtime_identity_mismatch_total",
    "Report requests where target IP does NOT match primary runtime IP",
    [],
)

# ── FASE 29.4.2: Report Presentation Classification Metrics ────
REPORT_MODEL_CLASSIFICATION_TOTAL = Counter(
    "ailab_report_model_classification_total",
    "Report model classification: active/disabled/discovered",
    ["status"],
)
REPORT_NODE_CLASSIFICATION_TOTAL = Counter(
    "ailab_report_node_classification_total",
    "Report node classification: active/inventory",
    ["status"],
)
REPORT_DATA_QUALITY_TOTAL = Counter(
    "ailab_report_data_quality_total",
    "Report data quality level: complete/partial/minimal",
    ["quality"],
)


def record_report_model_classification(status: str) -> None:
    REPORT_MODEL_CLASSIFICATION_TOTAL.labels(status=status or "unknown").inc()


def record_report_node_classification(status: str) -> None:
    REPORT_NODE_CLASSIFICATION_TOTAL.labels(status=status or "unknown").inc()


def record_report_data_quality(quality: str) -> None:
    REPORT_DATA_QUALITY_TOTAL.labels(quality=quality or "unknown").inc()

# ── FASE 28.2: Executor Readonly Runtime Metrics ────────────
EXECUTOR_COMMANDS_TOTAL = Counter(
    "ailab_executor_commands_total",
    "Comandos ejecutados por el readonly executor",
    ["result", "risk"],
)
EXECUTOR_BLOCKED_TOTAL = Counter(
    "ailab_executor_blocked_total",
    "Comandos bloqueados por el executor",
    ["reason"],
)
EXECUTOR_GOVERNANCE_BLOCKS = Counter(
    "ailab_executor_governance_blocks_total",
    "Acciones bloqueadas por governance del executor",
    ["intent"],
)
EXECUTOR_DRY_RUN_TOTAL = Counter(
    "ailab_executor_dry_run_total",
    "Dry-runs del executor por modo",
    ["reason"],
)
EXECUTOR_DURATION = Histogram(
    "ailab_executor_duration_ms",
    "Duracion de ejecucion del executor",
    ["mode"],
    buckets=(10, 50, 100, 500, 1000, 5000, 15000, 30000),
)
EXECUTOR_VALIDATION_FAILURES = Counter(
    "ailab_executor_validation_failures_total",
    "Fallos de validacion de comandos en el executor",
    ["reason"],
)

# ── FASE 28.2: Recorders ───────────────────────────────────

def record_executor_command(result: str, risk: str) -> None:
    EXECUTOR_COMMANDS_TOTAL.labels(result=result, risk=risk).inc()


def record_executor_blocked(reason: str) -> None:
    EXECUTOR_BLOCKED_TOTAL.labels(reason=reason).inc()


def record_executor_governance_block(intent: str) -> None:
    EXECUTOR_GOVERNANCE_BLOCKS.labels(intent=intent).inc()


def record_executor_dry_run(reason: str) -> None:
    EXECUTOR_DRY_RUN_TOTAL.labels(reason=reason).inc()


def record_executor_duration(mode: str, duration_ms: float) -> None:
    EXECUTOR_DURATION.labels(mode=mode).observe(float(duration_ms))


def record_executor_validation_failure(reason: str) -> None:
    EXECUTOR_VALIDATION_FAILURES.labels(reason=reason).inc()


# ── FASE 28.3: Sandbox Write Runtime Metrics ─────────────
SANDBOX_MUTATIONS_TOTAL = Counter(
    "ailab_sandbox_mutations_total",
    "Mutaciones ejecutadas en el sandbox",
    ["type", "result"],
)
SANDBOX_ROLLBACKS_TOTAL = Counter(
    "ailab_sandbox_rollbacks_total",
    "Rollbacks ejecutados en el sandbox",
    ["reason"],
)
SANDBOX_POLICY_DENIED_TOTAL = Counter(
    "ailab_sandbox_policy_denied_total",
    "Operaciones sandbox denegadas por governance",
    ["intent", "reason"],
)
SANDBOX_ARTIFACTS_TOTAL = Gauge(
    "ailab_sandbox_artifacts_total",
    "Numero total de artefactos registrados en el sandbox",
)
SANDBOX_ESCAPE_ATTEMPTS_TOTAL = Counter(
    "ailab_sandbox_escape_attempts_total",
    "Intentos de escape del sandbox detectados",
    ["detection_method"],
)
SANDBOX_CHECKSUM_MISMATCH_TOTAL = Counter(
    "ailab_sandbox_checksum_mismatch_total",
    "Checksums que no coinciden tras restore en sandbox",
)
SANDBOX_MUTATION_DURATION_SECONDS = Histogram(
    "ailab_sandbox_mutation_duration_seconds",
    "Duracion de las mutaciones sandbox",
    ["type"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
)

# ── FASE 28.3: Recorders ────────────────────────────────

def record_sandbox_mutation(mutation_type: str, result: str) -> None:
    SANDBOX_MUTATIONS_TOTAL.labels(type=mutation_type, result=result).inc()


def record_sandbox_rollback(reason: str) -> None:
    SANDBOX_ROLLBACKS_TOTAL.labels(reason=reason).inc()


def record_sandbox_policy_denied(intent: str, reason: str) -> None:
    SANDBOX_POLICY_DENIED_TOTAL.labels(intent=intent, reason=reason).inc()


def record_sandbox_artifact() -> None:
    SANDBOX_ARTIFACTS_TOTAL.inc()


def record_sandbox_escape_attempt(method: str) -> None:
    SANDBOX_ESCAPE_ATTEMPTS_TOTAL.labels(detection_method=method).inc()


def record_sandbox_checksum_mismatch() -> None:
    SANDBOX_CHECKSUM_MISMATCH_TOTAL.inc()


def record_sandbox_mutation_duration(mutation_type: str, seconds: float) -> None:
    SANDBOX_MUTATION_DURATION_SECONDS.labels(type=mutation_type).observe(float(seconds))


# ── FASE 29.3.1: Routing Tightening Recorders ──

def record_greeting_fastpath() -> None:
    GREETING_FASTPATH_TOTAL.inc()


def record_qwen_escalation(reason: str) -> None:
    QWEN_ESCALATION_TOTAL.labels(reason=reason).inc()


def record_llama_fastpath() -> None:
    LLAMA_FASTPATH_TOTAL.inc()


# ── FASE 29.0: Gateway Lifecycle Recorders ──────────────────

def record_gateway_boot() -> None:
    GATEWAY_BOOT_TOTAL.inc()
    GATEWAY_UPTIME.set(0)


def record_gateway_clean_shutdown() -> None:
    GATEWAY_CLEAN_SHUTDOWN.inc()


def record_gateway_unclean_shutdown() -> None:
    GATEWAY_UNCLEAN_SHUTDOWN.inc()


def record_gateway_singleton_violation() -> None:
    GATEWAY_SINGLETON_VIOLATION.inc()


def record_port_conflict() -> None:
    GATEWAY_PORT_CONFLICT.inc()


def record_residency_hit(model: str) -> None:
    RESIDENCY_HITS.labels(model=model).inc()


def record_residency_miss(model: str) -> None:
    RESIDENCY_MISSES.labels(model=model).inc()


def record_model_load_time(model: str, seconds: float) -> None:
    MODEL_LOAD_SECONDS.labels(model=model).observe(seconds)


def record_queue_wait(model: str, seconds: float) -> None:
    QUEUE_WAIT_SECONDS.labels(model=model).observe(seconds)


def record_tokens_per_second(model: str, tps: float) -> None:
    TOKENS_PER_SECOND.labels(model=model).set(tps)


def record_stream_first_chunk(model: str, latency_ms: int) -> None:
    STREAM_FIRST_CHUNK_LATENCY.labels(model=model).observe(float(latency_ms))


def record_stream_chunk_cadence(model: str, cadence_ms: int) -> None:
    STREAM_CHUNK_CADENCE.labels(model=model).observe(float(cadence_ms))


def record_stream_finalization_mismatch() -> None:
    STREAM_FINALIZATION_MISMATCH.inc()


# ── FASE 30G: Operational Reporting Discipline Metrics ──────
REPORT_FORBIDDEN_RECOMMENDATION_BLOCKED = Counter(
    "ailab_report_forbidden_recommendation_blocked_total",
    "Recomendaciones bloqueadas por politica en reportes operacionales",
    ["tool"],
)

# ── FASE 31C: Operational Reporting Discipline Metrics ──────
REPORTING_TOTAL = Counter(
    "ailab_reporting_total",
    "Reportes operacionales generados por modo",
    ["mode"],
)
REPORTING_CONFIDENCE = Counter(
    "ailab_reporting_confidence",
    "Reportes por nivel de confianza",
    ["level"],
)
REPORTING_DEGRADED_TOTAL = Counter(
    "ailab_reporting_degraded_total",
    "Total de dominios degradados reportados",
)
REPORTING_UNKNOWN_TOTAL = Counter(
    "ailab_reporting_unknown_total",
    "Total de dominios desconocidos reportados",
)
REPORTING_EXPLAINABILITY_SCORE = Histogram(
    "ailab_reporting_explainability_score",
    "Puntuacion de explainabilidad del reporte",
    buckets=(0, 25, 50, 75, 100),
)
REPORTING_CONSISTENCY_SCORE = Histogram(
    "ailab_reporting_consistency_score",
    "Puntuacion de consistencia del reporte",
    buckets=(0, 25, 50, 75, 100),
)
REPORTING_GOVERNANCE_TOTAL = Counter(
    "ailab_reporting_governance_total",
    "Governance summaries generados",
)


# ── FASE 30H: Runtime Evidence Enforcement Metrics ──────────
REPORT_EVIDENCE_GUARD_TOTAL = Counter(
    "ailab_report_evidence_guard_total",
    "Veces que el evidence guard fue invocado en reportes",
    [],
)

REPORT_EVIDENCE_GUARD_SCOPED_TOTAL = Counter(
    "ailab_report_evidence_guard_scoped_total",
    "Evidence guard executions with scope labels",
    ["action", "model", "route_family", "guard_scope"],
)
REPORT_UNVERIFIED_CLAIM_TOTAL = Counter(
    "ailab_report_unverified_claim_total",
    "Afirmaciones no verificadas detectadas por el evidence guard",
    ["count"],
)
REPORT_EVIDENCE_SCORE = Histogram(
    "ailab_report_evidence_score",
    "Puntuacion de evidencia del reporte (1.0 = todas verificadas)",
    [],
    buckets=(0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0),
)
REPORT_HALLUCINATION_SUPPRESSED_TOTAL = Counter(
    "ailab_report_hallucination_suppressed_total",
    "Veces que se suprimio un reporte con riesgo de alucinacion alto",
    [],
)


def record_report_forbidden_recommendation(tool: str) -> None:
    REPORT_FORBIDDEN_RECOMMENDATION_BLOCKED.labels(tool=tool or "unknown").inc()


# ── FASE 30H: Evidence Guard Recorders ──────────────────────

RUNTIME_CONTEXT_AUTOINJECTED_TOTAL = Counter(
    "ailab_runtime_context_autoinjected_total",
    "Veces que se auto-inyecto contexto runtime minimo por deteccion de intencion",
    [],
)


def record_runtime_context_autoinjected() -> None:
    RUNTIME_CONTEXT_AUTOINJECTED_TOTAL.inc()


def record_report_evidence_guard_scoped(
    action: str,
    model: str | None = None,
    route_family: str | None = None,
    guard_scope: str | None = None,
) -> None:
    REPORT_EVIDENCE_GUARD_SCOPED_TOTAL.labels(
        action=action or "unknown",
        model=model or "unknown",
        route_family=route_family or "unknown",
        guard_scope=guard_scope or "fallback_disabled",
    ).inc()


def record_report_evidence_score(score: float) -> None:
    REPORT_EVIDENCE_SCORE.observe(float(score))


def record_report_evidence_guard() -> None:
    REPORT_EVIDENCE_GUARD_TOTAL.inc()


def record_report_unverified_claim(count: int) -> None:
    REPORT_UNVERIFIED_CLAIM_TOTAL.labels(count=str(count)).inc()


def record_report_hallucination_suppressed() -> None:
    REPORT_HALLUCINATION_SUPPRESSED_TOTAL.inc()


# ── FASE 30A: Runtime State & Maturity Metrics ────────────
RUNTIME_MATURITY_STATE = Gauge(
    "ailab_runtime_maturity_state",
    "Current runtime maturity level (0=booting, 1=stabilizing, 2=operational, 3=degraded, 4=emergency, 5=shutdown)",
)
RUNTIME_MATURITY_PHASE = Gauge(
    "ailab_runtime_maturity_phase",
    "Current runtime implementation phase encoded as numeric gauge",
)


def record_maturity_state(maturity: str) -> None:
    state_map = {
        "booting": 0, "stabilizing": 1, "operational": 2,
        "degraded": 3, "emergency": 4, "shutdown": 5,
    }
    RUNTIME_MATURITY_STATE.set(float(state_map.get(maturity, 2)))


def record_maturity_phase(phase: str) -> None:
    try:
        phase_num = float(phase.replace("A", ".5").replace("B", ".6").replace("C", ".7"))
        RUNTIME_MATURITY_PHASE.set(phase_num)
    except (ValueError, AttributeError):
        RUNTIME_MATURITY_PHASE.set(0.0)


# ── FASE 30B: Model State Awareness Metrics ────────────
RUNTIME_MODEL_STATE = Gauge(
    "ailab_runtime_model_state",
    "Current operational state per model (0=discoverable, 1=loaded, 2=active, 3=disabled, 4=unavailable)",
    ["model", "status"],
)


def record_model_state(model_id: str, status: str) -> None:
    state_map = {
        "discoverable": 0, "loaded": 1, "active": 2,
        "disabled": 3, "unavailable": 4,
    }
    RUNTIME_MODEL_STATE.labels(model=model_id, status=status).set(
        float(state_map.get(status, 0))
    )


# ── FASE 30I: Runtime Sensor Fusion Metrics ─────────────
SENSOR_FUSION_TOTAL = Counter(
    "ailab_sensor_fusion_total",
    "Sensor fusion collection events by source and status",
    ["source", "status"],
)
SENSOR_FUSION_DURATION_MS = Histogram(
    "ailab_sensor_fusion_duration_ms",
    "Duration of sensor fusion per source in ms",
    ["source"],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000),
)
SENSOR_FUSION_MISSING_TOTAL = Counter(
    "ailab_sensor_fusion_missing_source_total",
    "Missing sources during sensor fusion collection",
    ["source"],
)
OBSERVED_RUNTIME_CONTEXT_SIZE = Gauge(
    "ailab_observed_runtime_context_size_bytes",
    "Size in bytes of the OBSERVED_RUNTIME JSON snapshot",
)


def record_sensor_fusion(source: str, status: str) -> None:
    SENSOR_FUSION_TOTAL.labels(source=source, status=status).inc()


def record_sensor_fusion_duration(source: str, duration_ms: float) -> None:
    SENSOR_FUSION_DURATION_MS.labels(source=source).observe(float(duration_ms))


def record_sensor_fusion_missing(source: str) -> None:
    SENSOR_FUSION_MISSING_TOTAL.labels(source=source).inc()


def record_observed_runtime_size(size_bytes: int) -> None:
    OBSERVED_RUNTIME_CONTEXT_SIZE.set(float(size_bytes))


# ── FASE 30I-F: Cognitive Compression Metrics ─────────────
COGNITIVE_SUMMARY_TOTAL = Counter(
    "ailab_cognitive_summary_total",
    "Cognitive summary generation events by status",
    ["status"],
)
COGNITIVE_SUMMARY_SIGNAL_COUNT = Counter(
    "ailab_cognitive_summary_signal_count",
    "Compressed signal count by severity",
    ["severity"],
)
COGNITIVE_SUMMARY_CONFIDENCE = Counter(
    "ailab_cognitive_summary_confidence",
    "Cognitive summary generations by confidence level",
    ["level"],
)
COGNITIVE_SUMMARY_DURATION_MS = Histogram(
    "ailab_cognitive_summary_generation_duration_ms",
    "Duration of cognitive summary generation in ms",
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000),
)


def record_cognitive_summary(status: str) -> None:
    COGNITIVE_SUMMARY_TOTAL.labels(status=status).inc()


def record_cognitive_summary_signal(severity: str) -> None:
    COGNITIVE_SUMMARY_SIGNAL_COUNT.labels(severity=severity).inc()


def record_cognitive_summary_confidence(level: str) -> None:
    COGNITIVE_SUMMARY_CONFIDENCE.labels(level=level).inc()


def record_cognitive_summary_duration(duration_ms: float) -> None:
    COGNITIVE_SUMMARY_DURATION_MS.observe(float(duration_ms))


# ── FASE 30I-F0: Model Routing Cleanup Metrics ─────────────
DEPRECATED_MODEL_ROUTING_TOTAL = Counter(
    "ailab_deprecated_model_routing_total",
    "Deprecated model routing attempts by action",
    ["action"],
)
OPERATIONAL_MODEL_SELECTED_TOTAL = Counter(
    "ailab_operational_model_selected_total",
    "Operational model selections (llama-3.1-8b)",
)
CODING_MODEL_SELECTED_TOTAL = Counter(
    "ailab_coding_model_selected_total",
    "Coding model selections (qwen2.5-coder-14b)",
)


# ── FASE 30I-G: Runtime Grounding Metrics ─────────────
RUNTIME_GROUNDING_VALIDATION_TOTAL = Counter(
    "ailab_runtime_grounding_validation_total",
    "Runtime grounding validation events by model and route",
    ["model", "route_family", "entity_type"],
)
RUNTIME_GROUNDING_PASSED_TOTAL = Counter(
    "ailab_runtime_grounding_passed_total",
    "Runtime grounding validation passes",
    ["model", "route_family"],
)
RUNTIME_GROUNDING_REJECTED_TOTAL = Counter(
    "ailab_runtime_grounding_rejected_total",
    "Runtime grounding validation rejections",
    ["model", "route_family", "entity_type"],
)
RUNTIME_GROUNDING_REJECTION_REASON = Counter(
    "ailab_runtime_grounding_rejection_reason",
    "Runtime grounding rejection by reason",
    ["reason"],
)
RUNTIME_GROUNDING_UNKNOWN_STATE_TOTAL = Counter(
    "ailab_runtime_grounding_unknown_state_total",
    "Unknown state responses by state type",
    ["state"],
)


def record_deprecated_model_routing(action: str) -> None:
    DEPRECATED_MODEL_ROUTING_TOTAL.labels(action=action).inc()


def record_operational_model_selected() -> None:
    OPERATIONAL_MODEL_SELECTED_TOTAL.inc()


def record_coding_model_selected() -> None:
    CODING_MODEL_SELECTED_TOTAL.inc()


# ── FASE 31E: Entity State Taxonomy Metrics ─────────────
ENTITY_REGISTRY_TOTAL = Gauge(
    "ailab_entity_registry_total",
    "Entity registry count by entity type and entity state",
    ["entity_type", "entity_state"],
)
ENTITY_ACTIVE_TOTAL = Gauge(
    "ailab_entity_active_total",
    "Active entities by entity type",
    ["entity_type"],
)
ENTITY_INVENTORY_TOTAL = Gauge(
    "ailab_entity_inventory_total",
    "Inventory-only entities by entity type",
    ["entity_type"],
)
ENTITY_DISCOVERABLE_TOTAL = Gauge(
    "ailab_entity_discoverable_total",
    "Discoverable entities by entity type",
    ["entity_type"],
)
ENTITY_DEPRECATED_TOTAL = Gauge(
    "ailab_entity_deprecated_total",
    "Deprecated entities by entity type",
    ["entity_type"],
)
ENTITY_STALE_TOTAL = Gauge(
    "ailab_entity_stale_total",
    "Stale entities by entity type",
    ["entity_type"],
)
ENTITY_CONFIDENCE = Gauge(
    "ailab_entity_confidence",
    "Entity registry confidence score 0.0-1.0",
)
ENTITY_ROUTABLE_TOTAL = Gauge(
    "ailab_entity_routable_total",
    "Routable entities by entity type",
    ["entity_type"],
)


_CONFIDENCE_VALUE = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.0}


def record_entity_registry_metrics(registry: list[dict]) -> None:
    from collections import Counter
    type_state = Counter()
    type_active = Counter()
    type_inventory = Counter()
    type_discoverable = Counter()
    type_deprecated = Counter()
    type_stale = Counter()
    type_routable = Counter()
    confidences = set()

    for e in registry:
        etype = e.get("entity_type", "unknown")
        estate = e.get("operational_state", "unknown")
        type_state[(etype, estate)] += 1
        if estate == "active":
            type_active[etype] += 1
        if e.get("inventory_state") in ("inventory", "expected_offline") and not e.get("routable"):
            type_inventory[etype] += 1
        if e.get("discoverability") == "discoverable":
            type_discoverable[etype] += 1
        if e.get("deprecated"):
            type_deprecated[etype] += 1
        if e.get("freshness") in ("stale", "expired", "unavailable"):
            type_stale[etype] += 1
        if e.get("routable"):
            type_routable[etype] += 1
        confidences.add(e.get("confidence", "unknown"))

    for (etype, estate), count in type_state.items():
        ENTITY_REGISTRY_TOTAL.labels(entity_type=etype, entity_state=estate).set(float(count))
    for etype, count in type_active.items():
        ENTITY_ACTIVE_TOTAL.labels(entity_type=etype).set(float(count))
    for etype, count in type_inventory.items():
        ENTITY_INVENTORY_TOTAL.labels(entity_type=etype).set(float(count))
    for etype, count in type_discoverable.items():
        ENTITY_DISCOVERABLE_TOTAL.labels(entity_type=etype).set(float(count))
    for etype, count in type_deprecated.items():
        ENTITY_DEPRECATED_TOTAL.labels(entity_type=etype).set(float(count))
    for etype, count in type_stale.items():
        ENTITY_STALE_TOTAL.labels(entity_type=etype).set(float(count))
    for etype, count in type_routable.items():
        ENTITY_ROUTABLE_TOTAL.labels(entity_type=etype).set(float(count))

    conf_values = [_CONFIDENCE_VALUE.get(c, 0.0) for c in confidences]
    avg_conf = sum(conf_values) / max(len(conf_values), 1)
    ENTITY_CONFIDENCE.set(avg_conf)


# ── FASE 30I-G: Grounding Recorders ─────────────

def record_runtime_grounding_validation(model: str, route_family: str, entity_type: str) -> None:
    RUNTIME_GROUNDING_VALIDATION_TOTAL.labels(
        model=model or "unknown",
        route_family=route_family or "unknown",
        entity_type=entity_type or "unknown",
    ).inc()


def record_runtime_grounding_passed(model: str, route_family: str) -> None:
    RUNTIME_GROUNDING_PASSED_TOTAL.labels(
        model=model or "unknown",
        route_family=route_family or "unknown",
    ).inc()


def record_runtime_grounding_rejected(model: str, route_family: str, entity_type: str) -> None:
    RUNTIME_GROUNDING_REJECTED_TOTAL.labels(
        model=model or "unknown",
        route_family=route_family or "unknown",
        entity_type=entity_type or "unknown",
    ).inc()


def record_runtime_grounding_rejection_reason(reason: str) -> None:
    RUNTIME_GROUNDING_REJECTION_REASON.labels(reason=reason or "unknown").inc()


def record_runtime_grounding_unknown_state(state: str) -> None:
    RUNTIME_GROUNDING_UNKNOWN_STATE_TOTAL.labels(state=state or "unknown").inc()


# ── FASE OBS-31A: Observability Source-of-Truth Audit Metrics ─────────────
OBSERVABILITY_AUDIT_TOTAL = Counter(
    "ailab_observability_audit_total",
    "Observability source-of-truth audit executions",
    ["audit_type", "status"],
)
OBSERVABILITY_DASHBOARD_HEALTH = Gauge(
    "ailab_observability_dashboard_health",
    "Dashboard health level (0=broken, 1=stale, 2=healthy)",
    ["dashboard_uid"],
)
OBSERVABILITY_PANEL_BROKEN_TOTAL = Counter(
    "ailab_observability_panel_broken_total",
    "Broken panels detected during dashboard audit",
    ["dashboard_uid", "reason"],
)
OBSERVABILITY_STALE_METRIC_TOTAL = Counter(
    "ailab_observability_stale_metric_total",
    "Stale metrics detected during metric inventory",
    ["domain"],
)
OBSERVABILITY_RUNTIME_DRIFT_TOTAL = Counter(
    "ailab_observability_runtime_drift_total",
    "Runtime ↔ Grafana drift events detected",
    ["drift_type", "severity"],
)
OBSERVABILITY_QUERY_VALIDATION_TOTAL = Counter(
    "ailab_observability_query_validation_total",
    "Query validation results by type and result",
    ["query_type", "result"],
)
OBSERVABILITY_DATASOURCE_HEALTH = Gauge(
    "ailab_observability_datasource_health",
    "Datasource health (0=down, 1=degraded, 2=up)",
    ["datasource_name"],
)
OBSERVABILITY_ALIGNMENT_SCORE = Gauge(
    "ailab_observability_alignment_score",
    "Runtime ↔ Grafana alignment score (0-100)",
)


def record_observability_audit(audit_type: str, status: str) -> None:
    OBSERVABILITY_AUDIT_TOTAL.labels(
        audit_type=audit_type or "unknown",
        status=status or "unknown",
    ).inc()


def record_observability_dashboard_health(dashboard_uid: str, health: int) -> None:
    OBSERVABILITY_DASHBOARD_HEALTH.labels(dashboard_uid=dashboard_uid or "unknown").set(float(health))


def record_observability_panel_broken(dashboard_uid: str, reason: str) -> None:
    OBSERVABILITY_PANEL_BROKEN_TOTAL.labels(
        dashboard_uid=dashboard_uid or "unknown",
        reason=reason or "unknown",
    ).inc()


def record_observability_stale_metric(domain: str) -> None:
    OBSERVABILITY_STALE_METRIC_TOTAL.labels(domain=domain or "unknown").inc()


def record_observability_runtime_drift(drift_type: str, severity: str) -> None:
    OBSERVABILITY_RUNTIME_DRIFT_TOTAL.labels(
        drift_type=drift_type or "unknown",
        severity=severity or "unknown",
    ).inc()


def record_observability_query_validation(query_type: str, result: str) -> None:
    OBSERVABILITY_QUERY_VALIDATION_TOTAL.labels(
        query_type=query_type or "unknown",
        result=result or "unknown",
    ).inc()


def record_observability_datasource_health(datasource_name: str, health: int) -> None:
    OBSERVABILITY_DATASOURCE_HEALTH.labels(datasource_name=datasource_name or "unknown").set(float(health))


def record_observability_alignment_score(score: float) -> None:
    OBSERVABILITY_ALIGNMENT_SCORE.set(float(max(0.0, min(100.0, score))))


# ── OBS-31A.4 Remediation metrics ──

OBSERVABILITY_REMEDIATION_TOTAL = Counter(
    "ailab_observability_remediation_total",
    "Total remediation items generated",
    ["domain", "severity"],
)
OBSERVABILITY_REMEDIATION_CRITICAL_TOTAL = Counter(
    "ailab_observability_remediation_critical_total",
    "Critical remediation items",
)
OBSERVABILITY_QUICK_WIN_TOTAL = Counter(
    "ailab_observability_quick_win_total",
    "Safe quick win remediation items",
)
OBSERVABILITY_HIGH_RISK_CHANGE_TOTAL = Counter(
    "ailab_observability_high_risk_change_total",
    "High-risk change remediation items",
)
OBSERVABILITY_TECHNICAL_DEBT_TOTAL = Counter(
    "ailab_observability_technical_debt_total",
    "Technical debt items count by domain",
    ["domain"],
)
OBSERVABILITY_REMEDIATION_SCORE = Gauge(
    "ailab_observability_remediation_score",
    "Observability remediation score 0-100",
)


def record_observability_remediation(domain: str, severity: str) -> None:
    OBSERVABILITY_REMEDIATION_TOTAL.labels(domain=domain, severity=severity).inc()


def record_observability_remediation_critical() -> None:
    OBSERVABILITY_REMEDIATION_CRITICAL_TOTAL.inc()


def record_observability_quick_win() -> None:
    OBSERVABILITY_QUICK_WIN_TOTAL.inc()


def record_observability_high_risk_change() -> None:
    OBSERVABILITY_HIGH_RISK_CHANGE_TOTAL.inc()


def record_observability_technical_debt(domain: str) -> None:
    OBSERVABILITY_TECHNICAL_DEBT_TOTAL.labels(domain=domain).inc()


def record_observability_remediation_score(score: float) -> None:
    OBSERVABILITY_REMEDIATION_SCORE.set(float(max(0.0, min(100.0, score))))


# ── OBS-31A.5 Execution metrics ──

OBSERVABILITY_EXECUTION_TOTAL = Counter(
    "ailab_observability_execution_total",
    "Total quick win execution attempts",
    ["domain", "status"],
)
OBSERVABILITY_EXECUTION_AUTO_TOTAL = Counter(
    "ailab_observability_execution_auto_total",
    "Auto-fix applied count",
    ["domain"],
)
OBSERVABILITY_EXECUTION_MANUAL_TOTAL = Counter(
    "ailab_observability_execution_manual_total",
    "Manual intervention required count",
    ["domain"],
)
OBSERVABILITY_EXECUTION_TIME = Gauge(
    "ailab_observability_execution_time_seconds",
    "Time since last execution batch",
)


def record_observability_execution(domain: str, status: str) -> None:
    OBSERVABILITY_EXECUTION_TOTAL.labels(
        domain=domain or "unknown",
        status=status or "unknown",
    ).inc()


def record_observability_execution_auto(domain: str) -> None:
    OBSERVABILITY_EXECUTION_AUTO_TOTAL.labels(domain=domain or "unknown").inc()


def record_observability_execution_manual(domain: str) -> None:
    OBSERVABILITY_EXECUTION_MANUAL_TOTAL.labels(domain=domain or "unknown").inc()


def record_observability_execution_time() -> None:
    OBSERVABILITY_EXECUTION_TIME.set(time.time())


# ── FASE 31B: Runtime Semantic Maturity metrics ──

RUNTIME_MATURITY_SCORE = Gauge(
    "ailab_runtime_maturity_score",
    "Runtime maturity score 0-100",
)
RUNTIME_CONFIDENCE = Gauge(
    "ailab_runtime_confidence_score",
    "Runtime confidence score 0.0-1.0",
    ["confidence_level"],
)
RUNTIME_DEGRADED_DOMAINS = Gauge(
    "ailab_runtime_degraded_domains_total",
    "Number of degraded domains",
)
RUNTIME_UNKNOWN_DOMAINS = Gauge(
    "ailab_runtime_unknown_domains_total",
    "Number of unknown domains",
)
RUNTIME_UNCERTAINTY = Counter(
    "ailab_runtime_uncertainty_total",
    "Uncertainty events by type",
    ["uncertainty_type"],
)
RUNTIME_OPERATIONAL_IMPACT = Gauge(
    "ailab_runtime_operational_impact",
    "Operational impact level (0=none, 1=low, 2=medium, 3=high, 4=critical)",
)
RUNTIME_SEMANTIC_STATE = Counter(
    "ailab_runtime_semantic_state_total",
    "Runtime semantic state distribution",
    ["runtime_state"],
)


_IMPACT_VALUES = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def record_runtime_maturity(maturity: dict[str, Any]) -> None:
    score = maturity.get("maturity_score", 0)
    RUNTIME_MATURITY_SCORE.set(float(max(0.0, min(100.0, score))))

    conf = maturity.get("confidence", "unknown")
    conf_val = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.0}.get(conf, 0.0)
    RUNTIME_CONFIDENCE.labels(confidence_level=conf).set(conf_val)

    degraded = maturity.get("degraded_domains", [])
    RUNTIME_DEGRADED_DOMAINS.set(float(len(degraded)))

    unknown = maturity.get("unknown_domains", [])
    RUNTIME_UNKNOWN_DOMAINS.set(float(len(unknown)))

    uncert = maturity.get("uncertainty_level", "unknown")
    RUNTIME_UNCERTAINTY.labels(uncertainty_type=uncert).inc()

    impact = maturity.get("operational_impact", "none")
    RUNTIME_OPERATIONAL_IMPACT.set(float(_IMPACT_VALUES.get(impact, 0)))

    state = maturity.get("runtime_state", "unknown")
    RUNTIME_SEMANTIC_STATE.labels(runtime_state=state).inc()


# ── FASE 31D: Runtime Topology Awareness Metrics ────────────
TOPOLOGY_NODES_TOTAL = Gauge(
    "ailab_topology_nodes_total",
    "Total topology nodes by node type",
    ["node_type"],
)
TOPOLOGY_EDGES_TOTAL = Gauge(
    "ailab_topology_edges_total",
    "Total topology edges by relationship",
    ["relationship"],
)
TOPOLOGY_DEGRADED_PATHS_TOTAL = Gauge(
    "ailab_topology_degraded_paths_total",
    "Total degraded paths in topology",
)
TOPOLOGY_AUTHORITY_CHAINS_TOTAL = Gauge(
    "ailab_topology_authority_chains_total",
    "Total authority chains",
)
TOPOLOGY_BLAST_RADIUS_TOTAL = Gauge(
    "ailab_topology_blast_radius_total",
    "Total blast radius affected nodes",
    ["severity"],
)
TOPOLOGY_CONFIDENCE_SCORE = Gauge(
    "ailab_topology_confidence_score",
    "Topology confidence score 0-100",
)
TOPOLOGY_INVENTORY_NODES_TOTAL = Gauge(
    "ailab_topology_inventory_nodes_total",
    "Total inventory-only topology nodes",
)


def record_topology_metrics(topology: dict[str, Any]) -> None:
    from collections import Counter
    nodes = topology.get("nodes", [])
    edges = topology.get("edges", [])
    degraded = topology.get("degraded_paths", [])

    type_counts = Counter(n.get("node_type", "unknown") for n in nodes)
    for ntype, count in type_counts.items():
        TOPOLOGY_NODES_TOTAL.labels(node_type=ntype).set(float(count))

    rel_counts = Counter(e.get("relationship", "unknown") for e in edges)
    for rel, count in rel_counts.items():
        TOPOLOGY_EDGES_TOTAL.labels(relationship=rel).set(float(count))

    TOPOLOGY_DEGRADED_PATHS_TOTAL.set(float(len(degraded)))
    TOPOLOGY_INVENTORY_NODES_TOTAL.set(float(sum(1 for n in nodes if n.get("inventory_only"))))

    try:
        from runtime.topology import build_authority_graph, calculate_blast_radius, calculate_topology_confidence
        authority = build_authority_graph()
        TOPOLOGY_AUTHORITY_CHAINS_TOTAL.set(float(authority.get("total_chains", 0)))
        blast = calculate_blast_radius()
        TOPOLOGY_BLAST_RADIUS_TOTAL.labels(severity=blast.get("severity", "low")).set(float(len(blast.get("affected_nodes", []))))
        conf = calculate_topology_confidence()
        TOPOLOGY_CONFIDENCE_SCORE.set(float(conf.get("overall_score", 0)))
    except ImportError:
        pass


# ── FASE 32A: Runtime UI Alignment Metrics ────────────
UI_ALIGNMENT_SCORE = Gauge(
    "ailab_ui_alignment_score",
    "UI alignment score 0-100 indicating how well UI matches runtime reality",
)
UI_HARDCODED_ENTITIES_TOTAL = Gauge(
    "ailab_ui_hardcoded_entities_total",
    "Total hardcoded inventory entities detected in UI",
)
UI_TOPOLOGY_DRIFT_TOTAL = Gauge(
    "ailab_ui_topology_drift_total",
    "Total topology drifts between UI and runtime",
)
UI_RUNTIME_MISMATCH_TOTAL = Gauge(
    "ailab_ui_runtime_mismatch_total",
    "Total runtime mismatches between UI entities and runtime entity registry",
)
UI_FAKE_INVENTORY_TOTAL = Gauge(
    "ailab_ui_fake_inventory_total",
    "Total fake inventory entries detected in UI (RTX5070, A100, etc)",
)

# ── FASE 32B: Grafana Semantic Cleanup Metrics ────────────
GRAFANA_ALIGNMENT_SCORE = Gauge(
    "ailab_grafana_alignment_score",
    "Grafana semantic alignment score 0-100 against runtime truth",
)
GRAFANA_FAKE_PANELS_TOTAL = Gauge(
    "ailab_grafana_fake_panels_total",
    "Total Grafana panels with fake GPU references (A100, H100, etc)",
)
GRAFANA_STALE_PANELS_TOTAL = Gauge(
    "ailab_grafana_stale_panels_total",
    "Total stale Grafana panels using deprecated metrics",
)
GRAFANA_ORPHAN_DATASOURCES_TOTAL = Gauge(
    "ailab_grafana_orphan_datasources_total",
    "Total orphan datasources referenced by Grafana dashboards",
)
GRAFANA_METRIC_DRIFT_TOTAL = Gauge(
    "ailab_grafana_metric_drift_total",
    "Total metric drift instances detected in Grafana dashboards",
)
GRAFANA_RUNTIME_ALIGNED_DASHBOARDS_TOTAL = Gauge(
    "ailab_grafana_runtime_aligned_dashboards_total",
    "Total Grafana dashboards marked as runtime-aligned",
)

# ── FASE 33A: Runtime Governance Registry Metrics ────────────
GOVERNANCE_SCORE = Gauge(
    "ailab_governance_score",
    "Runtime governance score 0-100",
)
GOVERNANCE_DEGRADED_DOMAINS_TOTAL = Gauge(
    "ailab_governance_degraded_domains_total",
    "Total degraded governance domains",
)
GOVERNANCE_RISKS_TOTAL = Gauge(
    "ailab_governance_risks_total",
    "Total active governance risks",
)
GOVERNANCE_CONTRACT_DRIFT_TOTAL = Gauge(
    "ailab_governance_contract_drift_total",
    "Total contract drift instances detected",
)
GOVERNANCE_STALE_AUTHORITY_TOTAL = Gauge(
    "ailab_governance_stale_authority_total",
    "Total stale authority entries",
)
GOVERNANCE_REMEDIATION_PENDING_TOTAL = Gauge(
    "ailab_governance_remediation_pending_total",
    "Total pending remediation items",
)
GOVERNANCE_CONFIDENCE_SCORE = Gauge(
    "ailab_governance_confidence_score",
    "Governance confidence score 0.0-1.0",
)

# ── FASE 33B: Runtime Pre-Pilot Validation Metrics ────────────
VALIDATION_SCORE = Gauge(
    "ailab_validation_score",
    "Runtime validation score 0-100",
)
VALIDATION_FAILED_INVARIANTS_TOTAL = Gauge(
    "ailab_validation_failed_invariants_total",
    "Total failed invariants in validation framework",
)
VALIDATION_FAILED_GATES_TOTAL = Gauge(
    "ailab_validation_failed_gates_total",
    "Total failed safety gates in validation framework",
)
VALIDATION_RUNTIME_REGRESSIONS_TOTAL = Gauge(
    "ailab_validation_runtime_regressions_total",
    "Total detected runtime regressions (validation/gov/obs/topology)",
)
VALIDATION_FAILURE_SURFACE_TOTAL = Gauge(
    "ailab_validation_failure_surface_total",
    "Total failure modes detected in failure surface analysis",
)
VALIDATION_PILOT_READINESS_SCORE = Gauge(
    "ailab_validation_pilot_readiness_score",
    "Pilot readiness score 0-100",
)
VALIDATION_DEGRADED_DOMAINS_TOTAL = Gauge(
    "ailab_validation_degraded_domains_total",
    "Total degraded domains impacting validation",
)

# ── FASE 34A: Runtime Operational Hardening Metrics ────────────
HARDENING_SCORE = Gauge(
    "ailab_hardening_score",
    "Runtime operational hardening score 0-100",
)
HARDENING_WATCHDOGS_TOTAL = Gauge(
    "ailab_hardening_watchdogs_total",
    "Total watchdogs evaluated in hardening layer",
)
HARDENING_WATCHDOGS_CRITICAL_TOTAL = Gauge(
    "ailab_hardening_watchdogs_critical_total",
    "Total critical watchdogs",
)
HARDENING_WATCHDOGS_DEGRADED_TOTAL = Gauge(
    "ailab_hardening_watchdogs_degraded_total",
    "Total degraded watchdogs",
)
HARDENING_TIMEOUT_GOVERNANCE_DEGRADED_TOTAL = Gauge(
    "ailab_hardening_timeout_governance_degraded_total",
    "Total timeout governance entries with degraded authority",
)
HARDENING_CONTAINMENT_MODE_ACTIVE = Gauge(
    "ailab_hardening_containment_mode_active",
    "1 if containment mode active, else 0",
)
HARDENING_INSTABILITY_EVENTS_TOTAL = Gauge(
    "ailab_hardening_instability_events_total",
    "Total operational instability events detected",
)

# ── FASE 28.4: Tool Contracts & Cross-Plan GC Metrics ────────────
TOOL_GOVERNANCE_SCORE = Gauge(
    "ailab_tool_governance_score",
    "Tool governance score 0-100",
)
INVALID_TOOL_CONTRACTS_TOTAL = Gauge(
    "ailab_invalid_tool_contracts_total",
    "Total invalid tool contracts detected",
)
ORPHAN_TOOLS_TOTAL = Gauge(
    "ailab_orphan_tools_total",
    "Total orphan tools (unreferenced by plans)",
)
ORPHAN_PLANS_TOTAL = Gauge(
    "ailab_orphan_plans_total",
    "Total orphan plans (invalid tool references)",
)
GC_CANDIDATES_TOTAL = Gauge(
    "ailab_gc_candidates_total",
    "Total GC candidates detected",
)
GC_PROTECTED_ARTIFACTS_TOTAL = Gauge(
    "ailab_gc_protected_artifacts_total",
    "Total protected artifacts (not eligible for GC)",
)
GC_SAFETY_SCORE = Gauge(
    "ailab_gc_safety_score",
    "GC safety score 0-100",
)
CROSSPLAN_REFERENCE_DRIFT_TOTAL = Gauge(
    "ailab_crossplan_reference_drift_total",
    "Total cross-plan reference drift instances",
)


def record_tool_gc_metrics(tool_gov: dict[str, Any], plan_reg: dict[str, Any], gc: dict[str, Any]) -> None:
    try:
        TOOL_GOVERNANCE_SCORE.set(float(tool_gov.get("tool_governance_score", 0.0) or 0.0))
        INVALID_TOOL_CONTRACTS_TOTAL.set(float(tool_gov.get("invalid_tool_contracts_total", 0) or 0))
        ORPHAN_TOOLS_TOTAL.set(float(tool_gov.get("orphan_tools_total", 0) or 0))
    except Exception:
        pass

    try:
        from runtime.plans.plan_registry import detect_orphan_plans
        ORPHAN_PLANS_TOTAL.set(float(len(detect_orphan_plans())))
    except Exception:
        pass

    inv = gc.get("inventory", {}) or {}
    candidates = gc.get("candidates", []) or []
    try:
        GC_CANDIDATES_TOTAL.set(float(len(candidates)))
        protected = sum(1 for it in (inv.get("items", []) or []) if it.get("protected"))
        GC_PROTECTED_ARTIFACTS_TOTAL.set(float(protected))
        GC_SAFETY_SCORE.set(float((gc.get("safety", {}) or {}).get("gc_safety_score", 0.0) or 0.0))
    except Exception:
        pass

    try:
        # Drift is 0 in this phase unless invalid references exist.
        drift = 0
        try:
            from runtime.plans.plan_registry import detect_invalid_plan_references
            drift += len(detect_invalid_plan_references())
        except Exception:
            pass
        CROSSPLAN_REFERENCE_DRIFT_TOTAL.set(float(drift))
    except Exception:
        pass


def record_governance_metrics(registry: dict[str, Any]) -> None:
    score_info = registry.get("governance_score_info", {})
    score = score_info.get("score", 0)
    GOVERNANCE_SCORE.set(float(max(0.0, min(100.0, score))))

    degraded = registry.get("degraded_domains", [])
    GOVERNANCE_DEGRADED_DOMAINS_TOTAL.set(float(len(degraded)))

    risks = registry.get("risks", [])
    active_risks = [r for r in risks if r.get("severity") in ("high", "medium", "critical")]
    GOVERNANCE_RISKS_TOTAL.set(float(len(active_risks)))

    drift = registry.get("drift", [])
    active_drift = [d for d in drift if d.get("drift_type") != "no_drift"]
    GOVERNANCE_CONTRACT_DRIFT_TOTAL.set(float(len(active_drift)))

    health = registry.get("health_summary", {})
    stale_authority = health.get("stale_authority", [])
    GOVERNANCE_STALE_AUTHORITY_TOTAL.set(float(len(stale_authority)))
    GOVERNANCE_REMEDIATION_PENDING_TOTAL.set(float(health.get("remediation_pending", 0)))

    confidence = health.get("confidence", "unknown")
    conf_val = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.0}.get(confidence, 0.0)
    GOVERNANCE_CONFIDENCE_SCORE.set(conf_val)


def record_validation_metrics(report: dict[str, Any]) -> None:
    score = report.get("validation_score", 0.0)
    VALIDATION_SCORE.set(float(max(0.0, min(100.0, score))))

    invariants = report.get("invariants", []) or []
    failed_invariants = [i for i in invariants if i.get("status") == "fail"]
    VALIDATION_FAILED_INVARIANTS_TOTAL.set(float(len(failed_invariants)))

    gates = report.get("safety_gates", []) or []
    failed_gates = [g for g in gates if g.get("status") == "fail"]
    VALIDATION_FAILED_GATES_TOTAL.set(float(len(failed_gates)))

    regressions = (report.get("regressions", {}) or {}).get("regressions_total", 0)
    VALIDATION_RUNTIME_REGRESSIONS_TOTAL.set(float(regressions or 0))

    failure_surface = report.get("failure_surface", {}) or {}
    VALIDATION_FAILURE_SURFACE_TOTAL.set(float(failure_surface.get("total_failure_modes", 0) or 0))

    pilot = report.get("pilot_readiness", {}) or {}
    VALIDATION_PILOT_READINESS_SCORE.set(float(pilot.get("pilot_readiness_score", 0.0) or 0.0))

    degraded = report.get("degraded_domains", []) or []
    VALIDATION_DEGRADED_DOMAINS_TOTAL.set(float(len(degraded)))


# ── FASE 34A: Runtime Operational Hardening metrics recorder ─────────


def record_hardening_metrics(report: dict[str, Any]) -> None:
    try:
        score = float(report.get("hardening_score", 0.0) or 0.0)
        HARDENING_SCORE.set(float(max(0.0, min(100.0, score))))
    except Exception:
        pass

    watchdogs = report.get("watchdogs", []) or []
    try:
        HARDENING_WATCHDOGS_TOTAL.set(float(len(watchdogs)))
        HARDENING_WATCHDOGS_CRITICAL_TOTAL.set(float(sum(1 for w in watchdogs if w.get("state") == "critical")))
        HARDENING_WATCHDOGS_DEGRADED_TOTAL.set(float(sum(1 for w in watchdogs if w.get("state") == "degraded")))
    except Exception:
        pass

    timeouts = report.get("timeouts", []) or []
    try:
        HARDENING_TIMEOUT_GOVERNANCE_DEGRADED_TOTAL.set(float(sum(1 for t in timeouts if t.get("authority_degraded"))))
    except Exception:
        pass

    containment = report.get("containment", {}) or {}
    try:
        HARDENING_CONTAINMENT_MODE_ACTIVE.set(1.0 if containment.get("containment_mode") else 0.0)
    except Exception:
        pass

    instability = report.get("instability", []) or []
    try:
        # Exclude the synthetic stable marker from the count.
        events = [e for e in instability if e.get("type") != "stable"]
        HARDENING_INSTABILITY_EVENTS_TOTAL.set(float(len(events)))
    except Exception:
        pass
