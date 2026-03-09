"""Google OAuth authentication for HTTP/SSE transports.

Uses FastMCP 3.x GoogleProvider from fastmcp.server.auth.providers.google.

stdio transport (Claude Code) continues using CALCS_API_TOKEN env var.
OAuth only applies when serving over HTTP/SSE to remote clients.
"""

import logging
import os

logger = logging.getLogger("calcs-api.auth")


def get_auth_provider(base_url: str = "http://localhost:8002"):
    """Create a Google OAuth provider if credentials are configured.

    Returns None if Google OAuth env vars are not set (auth disabled).

    Required env vars:
        GOOGLE_CLIENT_ID: Google OAuth client ID
        GOOGLE_CLIENT_SECRET: Google OAuth client secret

    Optional env vars:
        MCP_BASE_URL: Public base URL of the MCP server (default: http://localhost:8002)

    Args:
        base_url: The public base URL of the MCP server (used for OAuth redirects).
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.info("Google OAuth not configured (GOOGLE_CLIENT_ID/SECRET not set) — auth disabled")
        return None

    try:
        from fastmcp.server.auth.providers.google import GoogleProvider
    except ImportError:
        logger.warning(
            "GoogleProvider not available. Upgrade to fastmcp>=3.0.0 for OAuth support."
        )
        return None

    public_base = os.getenv("MCP_BASE_URL", base_url)

    try:
        provider = GoogleProvider(
            client_id=client_id,
            client_secret=client_secret,
            base_url=public_base,
        )
        logger.info(f"Google OAuth configured — base_url={public_base}")
        return provider
    except Exception as e:
        logger.warning(f"Failed to create GoogleProvider: {e}")
        return None
