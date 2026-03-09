#!/usr/bin/env python3
"""Calcs API MCP Server — retail analytics for A/B tests and rollout analyses.

Supports HTTP, SSE, and stdio transports. Google OAuth for HTTP/SSE;
bearer token via env var for stdio (Claude Code).
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from .client import CalcsApiClient
from .middleware import configure_middleware
from .resources import register_resources
from .prompts import register_prompts
from .tools import register_all_tools

# Load environment variables
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Logging to stderr (stdout reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("calcs-api")


# ── Lifespan: shared API client ───────────────────────────────────────

@lifespan
async def app_lifespan(server):
    """Initialize and clean up the shared API client."""
    token = os.getenv("CALCS_API_TOKEN")
    if not token:
        logger.error("CALCS_API_TOKEN environment variable is required")
        sys.exit(1)

    base_url = os.getenv("CALCS_API_BASE_URL", "https://staging-app.marketdial.dev/calcs")
    default_client = os.getenv("CALCS_DEFAULT_CLIENT", "")

    client = CalcsApiClient(base_url=base_url, token=token, default_client=default_client)
    logger.info(f"API client initialized — base_url={base_url}")
    if default_client:
        logger.info(f"Default client: {default_client}")

    try:
        yield {"api_client": client}
    finally:
        await client.close()
        logger.info("API client closed")


# ── FastMCP server setup ──────────────────────────────────────────────

mcp = FastMCP("calcs-api", lifespan=app_lifespan)

# Register middleware (caching, rate limiting, etc.)
configure_middleware(mcp)

# Register resources (glossary, workflow guide)
register_resources(mcp)

# Register prompts (analyze_test, compare_tests, etc.)
register_prompts(mcp)

# Register all tools from tool modules
register_all_tools(mcp)


# ── Transport entry points ────────────────────────────────────────────

def run_http():
    """HTTP transport (default) — for LM Studio and remote clients."""
    logger.info("Starting Calcs API MCP Server (HTTP Transport)...")
    mcp.run(transport="streamable-http", host="localhost", port=8002)


def run_sse():
    """SSE transport — backward compatibility."""
    logger.info("Starting Calcs API MCP Server (SSE Transport)...")
    mcp.run(transport="sse", host="localhost", port=8001)


def run_stdio():
    """stdio transport — for Claude Code and Claude Desktop."""
    logger.info("Starting Calcs API MCP Server (stdio Transport)...")
    mcp.run(transport="stdio")


def run():
    """Default entry point — stdio transport (works with Claude Code/Desktop)."""
    run_stdio()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        run_http()
    elif len(sys.argv) > 1 and sys.argv[1] == "--sse":
        run_sse()
    else:
        run_stdio()
