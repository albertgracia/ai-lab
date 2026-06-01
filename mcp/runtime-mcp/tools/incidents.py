from mcp.server.fastmcp import FastMCP
from .client import get_client, GATEWAY_URL, logger

def register(mcp: FastMCP):
    @mcp.tool(
        name="ailab_incidents_active",
        description="Returns active incident intelligence report (failures, offline nodes, degradations, correlations)",
    )
    def ailab_incidents_active() -> dict:
        client = get_client()
        url = f"{GATEWAY_URL}/runtime/incidents/report"
        try:
            resp = client.get(url)
            if resp.status_code != 200:
                return {"status": "unavailable", "error": f"HTTP {resp.status_code}"}
            return {"status": "ok", "data": resp.json()}
        except Exception as exc:
            logger.warning("incidents_active failed: %s", exc)
            return {"status": "unavailable", "error": str(exc)}
