from mcp.server.fastmcp import FastMCP
from .client import get_client, ROUTER_URL, logger

def register(mcp: FastMCP):
    @mcp.tool(
        name="ailab_operator_summary",
        description="Returns NOC-ready operator summary of AI-LAB runtime (services, nodes, GPU, watchdog)",
    )
    def ailab_operator_summary() -> dict:
        client = get_client()
        url = f"{ROUTER_URL}/runtime/reporting/operator-summary"
        try:
            resp = client.get(url)
            if resp.status_code != 200:
                return {"status": "unavailable", "error": f"HTTP {resp.status_code}"}
            return {"status": "ok", "data": resp.json()}
        except Exception as exc:
            logger.warning("operator_summary failed: %s", exc)
            return {"status": "unavailable", "error": str(exc)}
