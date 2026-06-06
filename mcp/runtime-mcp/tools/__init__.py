from __future__ import annotations

from functools import wraps
from time import perf_counter

from mcp.server.fastmcp import FastMCP

from metrics import record_tool_call
from . import incidents, latency, memory, operator, route_preview, runtime_health, slo, status


TOOL_MODULES = (
    status,
    runtime_health,
    route_preview,
    operator,
    incidents,
    slo,
    latency,
    memory,
)


def _register_instrumented(mcp: FastMCP, module, endpoint: str, bind: str, service: str) -> None:
    original_tool = mcp.tool

    def instrumented_tool(*args, **kwargs):
        decorator = original_tool(*args, **kwargs)
        declared_name = kwargs.get("name")

        def register_decorator(func):
            tool_name = declared_name or getattr(func, "__name__", "unknown")

            @wraps(func)
            def instrumented(*f_args, **f_kwargs):
                started = perf_counter()
                try:
                    result = func(*f_args, **f_kwargs)
                except Exception:
                    record_tool_call(
                        endpoint,
                        service,
                        tool_name,
                        "error",
                        perf_counter() - started,
                        bind=bind,
                    )
                    raise
                record_tool_call(
                    endpoint,
                    service,
                    tool_name,
                    "success",
                    perf_counter() - started,
                    bind=bind,
                )
                return result

            return decorator(instrumented)

        return register_decorator

    mcp.tool = instrumented_tool
    try:
        module.register(mcp)
    finally:
        mcp.tool = original_tool


def register_all(mcp: FastMCP, *, endpoint: str = "unknown", bind: str = "unknown", service: str = "unknown") -> None:
    for module in TOOL_MODULES:
        _register_instrumented(mcp, module, endpoint, bind, service)
