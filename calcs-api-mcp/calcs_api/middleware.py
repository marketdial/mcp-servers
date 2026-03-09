"""Custom middleware for the Calcs API MCP server.

FastMCP 3.x uses a base Middleware class with hook methods.
We implement timing and response size guarding as custom middleware.
"""

import logging
import time
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger("calcs-api.middleware")


class TimingMiddleware(Middleware):
    """Log the duration of each tool call."""

    async def on_call_tool(self, context: MiddlewareContext, call_next) -> Any:
        tool_name = context.message.name
        start = time.monotonic()
        result = await call_next(context)
        elapsed = (time.monotonic() - start) * 1000
        logger.info(f"Tool {tool_name} completed in {elapsed:.0f}ms")
        return result


class ResponseSizeGuardMiddleware(Middleware):
    """Warn on oversized tool responses. Acts as a safety net.

    Does not truncate (the summarizers handle that) — just logs warnings
    for debugging when responses exceed the soft limit.
    """

    def __init__(self, warn_chars: int = 100_000):
        super().__init__()
        self.warn_chars = warn_chars

    async def on_call_tool(self, context: MiddlewareContext, call_next) -> Any:
        result = await call_next(context)
        if isinstance(result, str) and len(result) > self.warn_chars:
            tool_name = context.message.name
            logger.warning(
                f"Tool {tool_name} returned {len(result):,} chars "
                f"(>{self.warn_chars:,} warning threshold)"
            )
        return result


def configure_middleware(mcp):
    """Register middleware with the FastMCP server."""
    try:
        mcp.add_middleware(TimingMiddleware())
        mcp.add_middleware(ResponseSizeGuardMiddleware(warn_chars=100_000))
        logger.info("Middleware registered: Timing, ResponseSizeGuard")
    except Exception as e:
        logger.warning(f"Failed to register middleware: {e}")
