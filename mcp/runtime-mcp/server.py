"""
AI-LAB MCP Semantic Gateway
Serves read-only MCP tools for AI-LAB runtime observability.

Architecture:
  OpenCode → MCP remote → ailab-mcp-server → AI-LAB Gateway/Router/Live-API
"""

import os
import sys
import logging
from tools.client import logger as _logger
from tools import register_all

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BIND_HOST = os.environ.get("AILAB_MCP_BIND", "127.0.0.1")
BIND_PORT = int(os.environ.get("AILAB_MCP_PORT", "8091"))
AUTH_TOKEN = os.environ.get("AILAB_MCP_TOKEN", "")
LOG_LEVEL = os.environ.get("AILAB_MCP_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

if not AUTH_TOKEN:
    _logger.info("AILAB_MCP_TOKEN not set — binding to 127.0.0.1 only (local dev mode)")
    BIND_HOST = "127.0.0.1"
else:
    _logger.info("AILAB_MCP_TOKEN is set — binding to %s", BIND_HOST)

# ---------------------------------------------------------------------------
# MCP App
# ---------------------------------------------------------------------------
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ailab-mcp-semantic-gateway",
    instructions="""Read-only MCP Semantic Gateway for AI-LAB.

Tools:
  - ailab_status:              Check gateway + router health
  - ailab_runtime_health:      Runtime health summary from gateway
  - ailab_route_preview:       Heuristic route classification (no LLM)
  - ailab_operator_summary:    NOC-ready operator summary
  - ailab_incidents_active:    Incident intelligence report
  - ailab_slo_status:          SLO health + violations
  - ailab_health_latency:      Latency stats + health score
  - ailab_memory_search:       Semantic search across Qdrant collections
""",
)

register_all(mcp)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    import uvicorn

    _logger.info("Starting ailab-mcp-semantic-gateway on %s:%s", BIND_HOST, BIND_PORT)
    _logger.info("Gateway URL: %s", os.environ.get("AILAB_GATEWAY_URL", "http://127.0.0.1:8008"))
    _logger.info("Router URL:  %s", os.environ.get("AILAB_ROUTER_URL", "http://127.0.0.1:8083"))
    _logger.info("Live-API URL: %s", os.environ.get("AILAB_LIVE_API_URL", "http://127.0.0.1:8084"))
    _logger.info("Streamable HTTP endpoint: http://%s:%s/mcp", BIND_HOST, BIND_PORT)

    app = mcp.streamable_http_app()
    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT, log_level=LOG_LEVEL.lower())

if __name__ == "__main__":
    main()
