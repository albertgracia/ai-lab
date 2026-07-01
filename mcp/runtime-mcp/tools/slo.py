from mcp.server.fastmcp import FastMCP
from .client import get_client, GATEWAY_URL, logger

def register(mcp: FastMCP):
    @mcp.tool(
        name="ailab_slo_status",
        description="Returns SLO health status, degradation level, and recent violations from the Gateway. Use to track service-level objective compliance and detect upcoming breaches. Output: {status, slo_state, violations} where slo_state contains current health per SLO and violations is a list of recent breach events. Individual endpoint failures return error details per field.",
    )
    def ailab_slo_status() -> dict:
        client = get_client()
        status_url = f"{GATEWAY_URL}/runtime/slo/status"
        violations_url = f"{GATEWAY_URL}/runtime/slo/violations"

        result = {"status": "ok", "slo_state": {}, "violations": []}

        try:
            resp = client.get(status_url)
            if resp.status_code == 200:
                result["slo_state"] = resp.json()
        except Exception as exc:
            logger.warning("slo_status /status failed: %s", exc)
            result["slo_state"] = {"error": str(exc)}

        try:
            resp = client.get(violations_url)
            if resp.status_code == 200:
                result["violations"] = resp.json()
        except Exception as exc:
            logger.warning("slo_status /violations failed: %s", exc)
            result["violations"] = {"error": str(exc)}

        return result
