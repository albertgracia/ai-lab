"""
ROUTER-HF-MODEL-POLICY-01: Compat adapter for runtime/models/model_policy.py.

This module is preserved for backward compatibility.
All routing decisions should use runtime.models.model_policy directly.

DEPRECATED: Use runtime.models.model_policy instead.
"""

from runtime.models.model_policy import (
    CANONICAL_MODELS,
    PROHIBITED_MODELS,
    FAST_MODEL,
    STRONG_MODEL,
    get_model_for_route,
    get_fast_model,
    get_fallback_model,
    get_degraded_model,
    get_coding_model,
    get_reasoning_model,
    get_tool_use_model,
    is_prohibited_model,
    validate_route_model_selection,
)

# Backward compatibility aliases
PRIMARY_OPERATIONAL_MODEL = FAST_MODEL
PRIMARY_CODING_MODEL = STRONG_MODEL
DEPRECATED_MODEL_PREFIX = "lmstudio-community/qwen2.5-coder-14b-instruct"

from runtime.models.model_registry import (
    DEPRECATED_QWEN_14B_ALIAS,
)

DEPRECATED_MODEL_IDS: frozenset[str] = frozenset({
    DEPRECATED_QWEN_14B_ALIAS,
})

OPERATIONAL_PROMPT_KEYWORDS: tuple[str, ...] = (
    "estado runtime", "estado gpu", "estado de ai-lab",
    "gpu", "rx9070", "rx7900xt",
    "temperatura", "vram", "potencia", "consumo", "fan", "watts",
    "gpu load", "estado gpu",
    "observabilidad", "observability",
    "topology", "topologia",
    "health", "sana", "salud",
    "confidence", "confianza",
    "freshness", "actualizacion",
    "sensors", "sensores",
    "prometheus", "grafana",
    "governance",
    "storage", "almacenamiento", "disco",
    "cluster state", "estado del cluster",
    "operational summary", "cognitive summary",
    "noc", "resumen operacional",
    "ai-lab runtime", "runtime ai-lab",
    "metricas", "metrica",
    "slo", "degradacion",
    "modelo activo", "modelos activos",
    "servicios", "servicio",
    "latencia", "ttfb",
    "streaming", "stream",
    "cómo está", "como esta",
    "tasa de error", "errores",
    "nodo", "inference",
    "backup", "archive", "archivo",
    "snapshot", "manifest",
)

CODING_PROMPT_KEYWORDS: tuple[str, ...] = (
    "implementa", "implementar",
    "refactoriza", "refactorizar",
    "corrige", "corregir", "arregla",
    "escribe codigo", "escribe código",
    "genera tests", "genera test",
    "analiza stacktrace", "analiza el error",
    "diff", "patch", "commit",
    "pytest", "pytest", "unittest",
    "architecture", "arquitectura",
    "parser", "schema",
    "python", "async", "dockerfile",
    "prometheus exporter",
    "clase", "funcion", "metodo",
    "api", "endpoint", "router",
    "middleware", "decorator",
    "optimiza", "optimizar",
    "debug", "debugging",
    "stacktrace", "traceback",
    "stack trace", "trace back",
)

RUNTIME_GROUNDED_KEYWORDS: tuple[str, ...] = (
    "estado", "situacion", "que paso",
    "como esta", "que esta pasando",
    "resumen", "report", "reporte",
    "informe", "informacion",
    "hay alguna", "hay algún",
    "puedo", "podemos",
    "que hacemos", "que hacer",
    "cómo está", "como esta",
    "qué pasa", "que pasa",
    "qué está pasando", "que esta pasando",
)


def is_operational_prompt(text: str) -> bool:
    if not text:
        return False
    t = text.lower().strip()
    for kw in OPERATIONAL_PROMPT_KEYWORDS:
        if kw in t:
            return True
    return False


def is_coding_prompt(text: str) -> bool:
    if not text:
        return False
    t = text.lower().strip()
    for kw in CODING_PROMPT_KEYWORDS:
        if kw in t:
            return True
    return False


def is_runtime_grounded_prompt(text: str) -> bool:
    if not text:
        return False
    t = text.lower().strip()
    for kw in RUNTIME_GROUNDED_KEYWORDS:
        if kw in t:
            return True
    return is_operational_prompt(text)


def is_deprecated_model(model_id: str | None) -> bool:
    from runtime.models.model_registry import is_deprecated_model as _reg
    return _reg(model_id)


def resolve_operational_model() -> str:
    return PRIMARY_OPERATIONAL_MODEL


def resolve_coding_model() -> str:
    return PRIMARY_CODING_MODEL


def validate_model_selection(
    task_type: str,
    model_id: str,
    route_family: str,
    user_text: str,
) -> str:
    """Validate and override model selection based on routing policy.

    Delegates to runtime.models.model_policy for prohibited model checks.

    Returns the validated model_id, possibly overridden.
    """
    if is_prohibited_model(model_id):
        if is_coding_prompt(user_text):
            return PRIMARY_CODING_MODEL
        return PRIMARY_OPERATIONAL_MODEL

    if is_coding_prompt(user_text):
        if "qwen" not in model_id.lower() and model_id != PRIMARY_CODING_MODEL:
            return PRIMARY_CODING_MODEL
        return model_id

    if is_operational_prompt(user_text):
        return PRIMARY_OPERATIONAL_MODEL

    if route_family in ("minimal", "observe", "greeting"):
        return PRIMARY_OPERATIONAL_MODEL

    return model_id
