import os
import logging
import httpx

GATEWAY_URL = os.environ.get("AILAB_GATEWAY_URL", "http://127.0.0.1:8008")
ROUTER_URL = os.environ.get("AILAB_ROUTER_URL", "http://127.0.0.1:8083")
LIVE_API_URL = os.environ.get("AILAB_LIVE_API_URL", "http://127.0.0.1:8084")

HEALTH_TIMEOUT = int(os.environ.get("AILAB_MCP_TIMEOUT", "5"))

logger = logging.getLogger("ailab-mcp-semantic-gateway")

_client: httpx.Client | None = None

def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=HEALTH_TIMEOUT)
    return _client
