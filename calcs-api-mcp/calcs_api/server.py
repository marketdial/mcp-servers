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
    """Initialize and clean up the shared API client.

    Supports two auth modes:
    1. AUTH0_PASSWORD — fetches a bearer token from Auth0 (auto-refreshes)
    2. CALCS_API_TOKEN — uses a static bearer token (fallback)
    """
    base_url = os.getenv("CALCS_API_BASE_URL", "https://staging-app.marketdial.dev/calcs")
    default_client = os.getenv("CALCS_DEFAULT_CLIENT", "")
    auth0_password = os.getenv("AUTH0_PASSWORD")
    token = os.getenv("CALCS_API_TOKEN")

    if not auth0_password and not token:
        logger.error("Either AUTH0_PASSWORD or CALCS_API_TOKEN must be set")
        sys.exit(1)

    client = await CalcsApiClient.create(
        base_url=base_url,
        default_client=default_client,
        token=token,
        auth0_password=auth0_password,
    )

    auth_mode = "Auth0 password grant" if auth0_password else "static token"
    logger.info(f"API client initialized — base_url={base_url}, auth={auth_mode}")
    if default_client:
        logger.info(f"Default client: {default_client}")

    try:
        yield {"api_client": client}
    finally:
        await client.close()
        logger.info("API client closed")


# ── Server factory ───────────────────────────────────────────────────

def _create_server(auth=None):
    """Create and configure a FastMCP server instance.

    Args:
        auth: Optional auth provider (e.g. GoogleProvider for HTTP/SSE).
    """
    server = FastMCP("calcs-api", lifespan=app_lifespan, auth=auth)
    configure_middleware(server)
    register_resources(server)
    register_prompts(server)
    register_all_tools(server)
    return server


# Default server (no auth) — used by stdio and as fallback for HTTP/SSE
mcp = _create_server()


# ── Transport entry points ────────────────────────────────────────────

def run_http():
    """HTTP transport — for LM Studio and remote clients.

    If GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set, Google OAuth
    is enabled and users must authenticate before accessing tools.
    """
    from .auth import get_auth_provider

    port = int(os.getenv("PORT", os.getenv("MCP_HTTP_PORT", "8080")))
    base_url = os.getenv("MCP_BASE_URL", f"http://localhost:{port}")
    auth = get_auth_provider(base_url=base_url)

    if auth:
        server = _create_server(auth=auth)
        logger.info(f"Starting Calcs API MCP Server (HTTP + OAuth) on port {port}...")
    else:
        server = mcp
        logger.info(f"Starting Calcs API MCP Server (HTTP, no auth) on port {port}...")

    server.run(transport="streamable-http", host="0.0.0.0", port=port)


def run_sse():
    """SSE transport — backward compatibility.

    Same OAuth behavior as HTTP: enabled if Google credentials are set.
    """
    from .auth import get_auth_provider

    port = int(os.getenv("PORT", os.getenv("MCP_SSE_PORT", "8001")))
    base_url = os.getenv("MCP_BASE_URL", f"http://localhost:{port}")
    auth = get_auth_provider(base_url=base_url)

    if auth:
        server = _create_server(auth=auth)
        logger.info(f"Starting Calcs API MCP Server (SSE + OAuth) on port {port}...")
    else:
        server = mcp
        logger.info(f"Starting Calcs API MCP Server (SSE, no auth) on port {port}...")

    server.run(transport="sse", host="0.0.0.0", port=port)


def run_stdio():
    """stdio transport — for Claude Code and Claude Desktop.

    No user-level auth needed; the process inherits the caller's
    environment (including CALCS_API_TOKEN).
    """
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
