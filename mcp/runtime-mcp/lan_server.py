"""
AI-LAB MCP LAN Gateway (read-only, token-auth)
Separate wrapper for LAN access. Does NOT affect the local MCP on :8091.
"""
import os
import sys
import logging
from starlette.responses import PlainTextResponse, Response
from tools.client import logger as _logger
from tools import register_all
from metrics import (
    MCPMetricsMiddleware,
    bootstrap_process_metrics,
    metrics_http_body,
    record_auth_failure,
    record_auth_success,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BIND_HOST = os.environ.get("AILAB_MCP_HOST", "127.0.0.1")
BIND_PORT = int(os.environ.get("AILAB_MCP_PORT", "8092"))
REQUIRE_TOKEN = os.environ.get("AILAB_MCP_REQUIRE_TOKEN", "true").lower() == "true"
AUTH_TOKEN = os.environ.get("AILAB_MCP_TOKEN", "")
LOG_LEVEL = os.environ.get("AILAB_MCP_LOG_LEVEL", "INFO").upper()
ENDPOINT = "8092"
BIND_KIND = "lan"
SERVICE_NAME = "lan"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

if REQUIRE_TOKEN and not AUTH_TOKEN:
    print("FATAL: AILAB_MCP_REQUIRE_TOKEN=true but AILAB_MCP_TOKEN is not set. Aborting.", flush=True)
    sys.exit(1)

if not AUTH_TOKEN:
    _logger.info("AILAB_MCP_TOKEN not set - binding to 127.0.0.1 only (local dev mode)")
    BIND_HOST = "127.0.0.1"
else:
    _logger.info("AILAB_MCP_TOKEN is set - binding to %s", BIND_HOST)

# ---------------------------------------------------------------------------
# MCP App
# ---------------------------------------------------------------------------
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    "ailab-mcp-lan-gateway",
    instructions="""Read-only MCP LAN Gateway for AI-LAB (token-auth required).

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
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=["*"],
    ),
)

register_all(mcp, endpoint=ENDPOINT, bind=BIND_KIND, service=SERVICE_NAME)


async def metrics_endpoint(_request):
    return PlainTextResponse(
        metrics_http_body(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# Token Auth Middleware
# ---------------------------------------------------------------------------
class TokenAuthMiddleware:
    def __init__(self, inner_app):
        self.inner_app = inner_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.inner_app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        x_token = headers.get(b"x-ailab-mcp-token", b"").decode()

        valid = (
            auth_header == f"Bearer {AUTH_TOKEN}" or
            auth_header == f"token {AUTH_TOKEN}" or
            x_token == AUTH_TOKEN
        ) if AUTH_TOKEN else True

        if not valid:
            record_auth_failure(ENDPOINT, SERVICE_NAME, bind=BIND_KIND)
            _logger.warning("Unauthorized request from %s", scope.get("client"))
            response = Response("Unauthorized", status_code=401)
            await response(scope, receive, send)
            return

        if REQUIRE_TOKEN:
            record_auth_success(ENDPOINT, SERVICE_NAME, bind=BIND_KIND)
        await self.inner_app(scope, receive, send)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    import uvicorn

    app = mcp.streamable_http_app()
    app.add_middleware(MCPMetricsMiddleware, endpoint=ENDPOINT, bind=BIND_KIND, service=SERVICE_NAME)

    if REQUIRE_TOKEN:
        app.add_middleware(TokenAuthMiddleware)

    app.add_route("/metrics", metrics_endpoint, methods=["GET"])
    bootstrap_process_metrics(ENDPOINT, BIND_KIND, SERVICE_NAME, auth_mode="token" if REQUIRE_TOKEN else "none")

    _logger.info("Starting ailab-mcp-lan-gateway on %s:%s", BIND_HOST, BIND_PORT)
    _logger.info("Require token: %s", REQUIRE_TOKEN)
    _logger.info("Gateway URL: %s", os.environ.get("AILAB_GATEWAY_URL", "http://127.0.0.1:8008"))
    _logger.info("Router URL:  %s", os.environ.get("AILAB_ROUTER_URL", "http://127.0.0.1:8083"))
    _logger.info("Live-API URL: %s", os.environ.get("AILAB_LIVE_API_URL", "http://127.0.0.1:8084"))
    _logger.info("Streamable HTTP endpoint: http://%s:%s/mcp", BIND_HOST, BIND_PORT)

    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT, log_level=LOG_LEVEL.lower())

if __name__ == "__main__":
    main()
