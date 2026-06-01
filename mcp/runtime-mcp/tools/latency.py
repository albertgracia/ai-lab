from mcp.server.fastmcp import FastMCP
from .client import get_client, GATEWAY_URL, logger

def register(mcp: FastMCP):
    @mcp.tool(
        name="ailab_health_latency",
        description="Returns runtime health score and latency statistics (p50/p95/max)",
    )
    def ailab_health_latency() -> dict:
        client = get_client()
        latency_url = f"{GATEWAY_URL}/runtime/health/latency"
        score_url = f"{GATEWAY_URL}/runtime/health/score"

        result = {"status": "ok", "latency": {}, "health_score": {}}

        try:
            resp = client.get(latency_url)
            if resp.status_code == 200:
                result["latency"] = resp.json()
        except Exception as exc:
            logger.warning("health_latency /latency failed: %s", exc)
            result["latency"] = {"error": str(exc)}

        try:
            resp = client.get(score_url)
            if resp.status_code == 200:
                result["health_score"] = resp.json()
        except Exception as exc:
            logger.warning("health_latency /score failed: %s", exc)
            result["health_score"] = {"error": str(exc)}

        return result
