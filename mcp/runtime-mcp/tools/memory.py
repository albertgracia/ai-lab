from mcp.server.fastmcp import FastMCP
from .client import get_client, LIVE_API_URL, logger

def register(mcp: FastMCP):
    @mcp.tool(
        name="ailab_memory_search",
        description="Semantic search across AI-LAB Qdrant collections (routing_history, incidents, cognitive_history)",
    )
    def ailab_memory_search(query: str, limit: int = 5) -> dict:
        if not query or not isinstance(query, str):
            return {"status": "error", "error": "query must be a non-empty string"}

        client = get_client()
        url = f"{LIVE_API_URL}/api/memory/search"

        try:
            resp = client.get(url, params={"q": query, "limit": min(limit, 20)})
            if resp.status_code != 200:
                return {"status": "unavailable", "error": f"HTTP {resp.status_code}"}
            return {"status": "ok", "data": resp.json()}
        except Exception as exc:
            logger.warning("memory_search failed: %s", exc)
            return {"status": "unavailable", "error": str(exc)}
