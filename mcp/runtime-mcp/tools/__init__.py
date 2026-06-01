from mcp.server.fastmcp import FastMCP

from . import status, runtime_health, route_preview
from . import operator, incidents, slo, latency, memory

def register_all(mcp: FastMCP):
    status.register(mcp)
    runtime_health.register(mcp)
    route_preview.register(mcp)
    operator.register(mcp)
    incidents.register(mcp)
    slo.register(mcp)
    latency.register(mcp)
    memory.register(mcp)
