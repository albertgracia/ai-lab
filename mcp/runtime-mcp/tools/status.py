from mcp.server.fastmcp import FastMCP
from .client import get_client, GATEWAY_URL, ROUTER_URL, logger

def register(mcp: FastMCP):
    @mcp.tool(
        name="ailab_status",
        description="Returns health status of AI-LAB Gateway and Router",
    )
    def ailab_status() -> dict:
        client = get_client()
        gateway_ok, gateway_code = False, 0
        router_ok, router_code = False, 0

        try:
            resp = client.get(f"{GATEWAY_URL}/health")
            gateway_code = resp.status_code
            if resp.status_code == 200:
                gateway_ok = resp.json().get("status") == "ok"
        except Exception as exc:
            logger.warning("gateway /health failed: %s", exc)

        try:
            resp = client.get(f"{ROUTER_URL}/health")
            router_code = resp.status_code
            if resp.status_code == 200:
                router_ok = resp.json().get("status") == "ok"
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
            "gateway": {"url": f"{GATEWAY_URL}/health", "ok": gateway_ok, "status_code": gateway_code},
            "router": {"url": f"{ROUTER_URL}/health", "ok": router_ok, "status_code": router_code},
        }
