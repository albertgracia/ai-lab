import re
from mcp.server.fastmcp import FastMCP
from .client import logger

_CODING_SIGNALS = re.compile(
    r"\b(?:python|go|typescript|javascript|rust|fastapi|systemd|pytest|"
    r"stacktrace|error|traceback|git|diff|refactor|código|codigo|"
    r"implementar|crear|script|debug|fix|bug|api|endpoint)\b",
    re.IGNORECASE,
)

_REASONING_SIGNALS = re.compile(
    r"\b(?:analiza|audita|riesgo|arquitectura|plan|diagnóstico|"
    r"root\s?cause|comparativa|optimizar|diseñar|analys|architecture|"
    r"complex|analyze|infraestructura)\b",
    re.IGNORECASE,
)

_TOOL_SIGNALS = re.compile(
    r"\b(?:tool|mcp|gitnexus|qdrant|consulta|buscar|impact|"
    r"semantic|router|gateway)\b",
    re.IGNORECASE,
)

def heuristic_route_preview(prompt: str) -> dict:
    text = prompt.strip()
    if _CODING_SIGNALS.search(text):
        return {"route_family": "coding", "confidence": 0.75, "reason": "detected coding/technical signals in prompt"}
    if _REASONING_SIGNALS.search(text):
        return {"route_family": "reasoning", "confidence": 0.70, "reason": "detected analysis/architecture signals in prompt"}
    if _TOOL_SIGNALS.search(text):
        return {"route_family": "tool_use", "confidence": 0.65, "reason": "detected tool/infrastructure signals in prompt"}
    if len(text) < 80:
        return {"route_family": "fast", "confidence": 0.60, "reason": "short prompt — classified as fast"}
    return {"route_family": "unknown", "confidence": 0.30, "reason": "no strong signals detected"}

def register(mcp: FastMCP):
    @mcp.tool(
        name="ailab_route_preview",
        description="Heuristic route preview — classifies a prompt without LLM inference",
    )
    def ailab_route_preview(prompt: str) -> dict:
        if not prompt or not isinstance(prompt, str):
            return {
                "status": "error", "error": "prompt must be a non-empty string",
                "executed_model_call": False, "preview_type": "heuristic_preview",
                "route_family": "unknown", "confidence": 0.0, "reason": "empty or invalid prompt",
            }

        log_prompt = prompt[:120].replace("\n", " ")
        logger.info("route_preview prompt=%.120s", log_prompt)

        preview = heuristic_route_preview(prompt)

        return {
            "status": "ok", "executed_model_call": False, "preview_type": "heuristic_preview",
            "route_family": preview["route_family"],
            "confidence": preview["confidence"],
            "reason": preview["reason"],
        }
