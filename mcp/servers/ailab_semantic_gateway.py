"""
[LEGACY] AI-LAB MCP Semantic Gateway — PoC Read-Only

STATUS: LEGACY — Do NOT use for new development.

This file is a Phase-1 proof-of-concept (MCP-SEMANTIC-GATEWAY-01).
It is NOT the active runtime. The active runtime runs at /mnt/mcp_server/
(systemd: ailab-mcp-semantic-gateway.service).

SOURCE OF TRUTH (MCP Runtime):
  Active runtime:  /mnt/mcp_server/
  Snapshot (repo): mcp/runtime-mcp/
  Legacy (repo):   mcp/servers/ailab_semantic_gateway.py

New tests and development MUST target mcp/runtime-mcp/tools/.
Do NOT add new tools or modify runtime logic in this file.

Exposes 3 read-only MCP tools (duplicated from runtime-mcp):
  1. ailab_status          — health check of gateway + router
  2. ailab_runtime_health  — runtime health summary (nodes, scores, watchdog)
  3. ailab_route_preview   — heuristic route classification (no LLM call)

Original FASE: MCP-SEMANTIC-GATEWAY-01
"""

import os
import re
import time
import logging
import json as json_mod
from contextlib import asynccontextmanager

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GATEWAY_URL = os.environ.get("AILAB_GATEWAY_URL", "http://127.0.0.1:8008")
ROUTER_URL = os.environ.get("AILAB_ROUTER_URL", "http://127.0.0.1:8083")
BIND_HOST = os.environ.get("AILAB_MCP_BIND", "127.0.0.1")
BIND_PORT = int(os.environ.get("AILAB_MCP_PORT", "8091"))
AUTH_TOKEN = os.environ.get("AILAB_MCP_TOKEN", "")

HEALTH_TIMEOUT = 3  # seconds
LOG_LEVEL = os.environ.get("AILAB_MCP_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ailab-mcp-semantic-gateway")

# If no token is set, restrict to localhost only
if not AUTH_TOKEN:
    logger.info("AILAB_MCP_TOKEN not set — binding to 127.0.0.1 only (local dev mode)")
    BIND_HOST = "127.0.0.1"
else:
    logger.info("AILAB_MCP_TOKEN is set — binding to %s", BIND_HOST)


# ---------------------------------------------------------------------------
# Shared HTTP client
# ---------------------------------------------------------------------------
_client: httpx.Client | None = None


def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=HEALTH_TIMEOUT)
    return _client


# ---------------------------------------------------------------------------
# Route preview heuristics (read-only, no LLM call)
# ---------------------------------------------------------------------------
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
    text_lower = text.lower()

    if _CODING_SIGNALS.search(text):
        return {
            "route_family": "coding",
            "confidence": 0.75,
            "reason": "detected coding/technical signals in prompt",
        }
    if _REASONING_SIGNALS.search(text):
        return {
            "route_family": "reasoning",
            "confidence": 0.70,
            "reason": "detected analysis/architecture signals in prompt",
        }
    if _TOOL_SIGNALS.search(text):
        return {
            "route_family": "tool_use",
            "confidence": 0.65,
            "reason": "detected tool/infrastructure signals in prompt",
        }
    if len(text) < 80:
        return {
            "route_family": "fast",
            "confidence": 0.60,
            "reason": "short prompt — classified as fast",
        }
    return {
        "route_family": "unknown",
        "confidence": 0.30,
        "reason": "no strong signals detected",
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ailab-mcp-semantic-gateway",
    instructions="""Read-only MCP Semantic Gateway for AI-LAB.

Tools:
  - ailab_status:          Check gateway + router health
  - ailab_runtime_health:  Runtime health summary from gateway
  - ailab_route_preview:   Heuristic route classification (no LLM call)
""",
)


@mcp.tool(
    name="ailab_status",
    description="Returns health status of AI-LAB Gateway and Router. Use as a first-line check to confirm the MCP backend is reachable. Output: {status, gateway, router} with status ok|degraded|unavailable. Gateway and router must both respond 200 with status=ok for overall ok.",
)
def ailab_status() -> dict:
    """Check gateway and router health endpoints."""
    client = get_client()
    gateway_ok = False
    gateway_code = 0
    router_ok = False
    router_code = 0

    # Gateway health
    try:
        resp = client.get(f"{GATEWAY_URL}/health")
        gateway_code = resp.status_code
        if resp.status_code == 200:
            data = resp.json()
            gateway_ok = data.get("status") == "ok"
    except Exception as exc:
        logger.warning("gateway /health failed: %s", exc)

    # Router health
    try:
        resp = client.get(f"{ROUTER_URL}/health")
        router_code = resp.status_code
        if resp.status_code == 200:
            data = resp.json()
            router_ok = data.get("status") == "ok"
    except Exception as exc:
        logger.warning("router /health failed: %s", exc)

    if gateway_ok and router_ok:
        status = "ok"
    elif gateway_ok or router_ok:
        status = "degraded"
    else:
        status = "unavailable"

    return {
        "status": status,
        "gateway": {
            "url": f"{GATEWAY_URL}/health",
            "ok": gateway_ok,
            "status_code": gateway_code,
        },
        "router": {
            "url": f"{ROUTER_URL}/health",
            "ok": router_ok,
            "status_code": router_code,
        },
    }


@mcp.tool(
    name="ailab_runtime_health",
    description="Returns detailed runtime health summary from AI-LAB Gateway. Use for deep observability: node health, health scores, watchdog state, and overall_health. Output: {status, source, data} where data contains per-node breakdown. May time out after 3s if gateway is overloaded.",
)
def ailab_runtime_health() -> dict:
    """Fetch runtime health/summary from the gateway."""
    client = get_client()
    url = f"{GATEWAY_URL}/runtime/health"

    try:
        resp = client.get(url, timeout=HEALTH_TIMEOUT)
        if resp.status_code != 200:
            return {
                "status": "unavailable",
                "source": url,
                "data": {},
                "error": f"HTTP {resp.status_code}",
            }
        data = resp.json()
        return {
            "status": "ok",
            "source": url,
            "data": data,
        }
    except httpx.TimeoutException:
        logger.warning("runtime health timed out after %ss", HEALTH_TIMEOUT)
        return {
            "status": "unavailable",
            "source": url,
            "data": {},
            "error": "timeout",
        }
    except Exception as exc:
        logger.warning("runtime health failed: %s", exc)
        return {
            "status": "unavailable",
            "source": url,
            "data": {},
            "error": str(exc),
        }


@mcp.tool(
    name="ailab_route_preview",
    description="Heuristic route preview — classifies a prompt into a route family (coding|reasoning|tool_use|fast|unknown) without making any LLM call. Use to decide which model or pipeline should handle a request before inference. Output: {status, route_family, confidence, reason}. Zero-cost classification via regex signals.",
)
def ailab_route_preview(prompt: str) -> dict:
    """Classify a prompt into a route family using local heuristics.
    No LLM call is made. Prompt is NOT stored in full in logs."""
    if not prompt or not isinstance(prompt, str):
        return {
            "status": "error",
            "error": "prompt must be a non-empty string",
            "executed_model_call": False,
            "preview_type": "heuristic_preview",
            "route_family": "unknown",
            "confidence": 0.0,
            "reason": "empty or invalid prompt",
        }

    # Truncate in logs (120 chars max)
    log_prompt = prompt[:120].replace("\n", " ")
    logger.info("route_preview prompt=%.120s", log_prompt)

    preview = heuristic_route_preview(prompt)

    return {
        "status": "ok",
        "executed_model_call": False,
        "preview_type": "heuristic_preview",
        "route_family": preview["route_family"],
        "confidence": preview["confidence"],
        "reason": preview["reason"],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    import uvicorn

    logger.info(
        "Starting ailab-mcp-semantic-gateway on %s:%s",
        BIND_HOST,
        BIND_PORT,
    )
    logger.info("Gateway URL: %s", GATEWAY_URL)
    logger.info("Router URL:  %s", ROUTER_URL)
    logger.info("Auth token:  %s", "set" if AUTH_TOKEN else "not set (dev mode)")
    logger.info("Streamable HTTP endpoint: http://%s:%s/mcp", BIND_HOST, BIND_PORT)

    app = mcp.streamable_http_app()
    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT, log_level=LOG_LEVEL.lower())


if __name__ == "__main__":
    main()
