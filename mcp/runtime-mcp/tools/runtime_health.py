import httpx
from mcp.server.fastmcp import FastMCP
from .client import get_client, GATEWAY_URL, HEALTH_TIMEOUT, logger

def register(mcp: FastMCP):
    @mcp.tool(
        name="ailab_runtime_health",
        description="Returns detailed runtime health summary from AI-LAB Gateway",
    )
    def ailab_runtime_health() -> dict:
        client = get_client()
        url = f"{GATEWAY_URL}/runtime/health"

        try:
            resp = client.get(url, timeout=HEALTH_TIMEOUT)
            if resp.status_code != 200:
                return {"status": "unavailable", "source": url, "data": {}, "error": f"HTTP {resp.status_code}"}
            data = resp.json()
            return {"status": "ok", "source": url, "data": data}
        except httpx.TimeoutException:
            logger.warning("runtime health timed out after %ss", HEALTH_TIMEOUT)
            return {"status": "unavailable", "source": url, "data": {}, "error": "timeout"}
        except Exception as exc:
            logger.warning("runtime health failed: %s", exc)
            return {"status": "unavailable", "source": url, "data": {}, "error": str(exc)}
