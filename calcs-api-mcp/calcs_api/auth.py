"""Google OAuth authentication for HTTP/SSE transports.

Uses FastMCP 3.x GoogleProvider from fastmcp.server.auth.providers.google.

stdio transport (Claude Code) continues using CALCS_API_TOKEN env var.
OAuth only applies when serving over HTTP/SSE to remote clients.
"""

import hashlib
import logging
import os
from collections.abc import Mapping, Sequence
from typing import Any, SupportsFloat

logger = logging.getLogger("calcs-api.auth")


class _SafeKeyFirestoreStore:
    """Wrapper around FirestoreStore that sanitizes keys for Firestore compatibility.

    MCP client IDs like 'https://claude.ai/oauth/mcp-oauth-client-metadata'
    contain forward slashes, which Firestore interprets as collection/document
    path separators. This wrapper hashes such keys into safe document IDs
    while preserving the AsyncKeyValue protocol.
    """

    def __init__(self, inner):
        self._inner = inner

    @staticmethod
    def _safe_key(key: str) -> str:
        """Convert a key with special characters into a Firestore-safe document ID."""
        if "/" in key or len(key) > 200:
            # Use SHA-256 hash prefix + sanitized suffix for readability
            h = hashlib.sha256(key.encode()).hexdigest()[:16]
            safe = key.replace("/", "_").replace(":", "_")[:60]
            return f"{safe}__{h}"
        return key

    async def get(self, key: str, *, collection: str | None = None) -> dict[str, Any] | None:
        return await self._inner.get(self._safe_key(key), collection=collection)

    async def get_many(self, keys: Sequence[str], *, collection: str | None = None) -> list[dict[str, Any] | None]:
        return await self._inner.get_many([self._safe_key(k) for k in keys], collection=collection)

    async def put(self, key: str, value: Mapping[str, Any], *, collection: str | None = None, ttl: SupportsFloat | None = None) -> None:
        return await self._inner.put(self._safe_key(key), value, collection=collection, ttl=ttl)

    async def put_many(self, keys: Sequence[str], values: Sequence[Mapping[str, Any]], *, collection: str | None = None, ttl: SupportsFloat | None = None) -> None:
        return await self._inner.put_many([self._safe_key(k) for k in keys], values, collection=collection, ttl=ttl)

    async def delete(self, key: str, *, collection: str | None = None) -> bool:
        return await self._inner.delete(self._safe_key(key), collection=collection)

    async def delete_many(self, keys: Sequence[str], *, collection: str | None = None) -> int:
        return await self._inner.delete_many([self._safe_key(k) for k in keys], collection=collection)

    async def ttl(self, key: str, *, collection: str | None = None) -> tuple[dict[str, Any] | None, float | None]:
        return await self._inner.ttl(self._safe_key(key), collection=collection)

    async def ttl_many(self, keys: Sequence[str], *, collection: str | None = None) -> list[tuple[dict[str, Any] | None, float | None]]:
        return await self._inner.ttl_many([self._safe_key(k) for k in keys], collection=collection)


def _get_firestore_storage():
    """Create a Firestore-backed storage for OAuth state persistence.

    On Cloud Run, the default file-based storage is ephemeral (lost on
    instance restart/deploy), causing "Client Not Registered" errors for
    returning users. Firestore provides durable storage that survives
    instance lifecycle events.

    Uses Application Default Credentials, which on Cloud Run maps to the
    runtime service account. Requires the Datastore User role.

    Returns None if Firestore is not available (falls back to file storage).
    """
    try:
        from key_value.aio.stores.firestore import FirestoreStore

        project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        store = FirestoreStore(
            project=project,
            default_collection="mcp-oauth-state",
        )
        # Wrap with key sanitizer to handle slashes in MCP client IDs
        safe_store = _SafeKeyFirestoreStore(store)
        logger.info("Using Firestore for OAuth state persistence")
        return safe_store
    except ImportError:
        logger.info("Firestore not available — using default file storage")
        return None
    except Exception as e:
        logger.warning(f"Failed to create Firestore store: {e} — using default file storage")
        return None


def get_auth_provider(base_url: str = "http://localhost:8002"):
    """Create a Google OAuth provider if credentials are configured.

    Returns None if Google OAuth env vars are not set (auth disabled).

    Required env vars:
        GOOGLE_CLIENT_ID: Google OAuth client ID
        GOOGLE_CLIENT_SECRET: Google OAuth client secret

    Optional env vars:
        MCP_BASE_URL: Public base URL of the MCP server (default: http://localhost:8002)
        MCP_ALLOWED_EMAILS: Comma-separated list of allowed email addresses.
            If not set, any Google account can authenticate.
            Example: "alice@company.com,bob@company.com"

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

    # Use Firestore for persistent OAuth state on Cloud Run
    client_storage = _get_firestore_storage()

    try:
        provider = GoogleProvider(
            client_id=client_id,
            client_secret=client_secret,
            base_url=public_base,
            required_scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
            ],
            client_storage=client_storage,
        )
        logger.info(f"Google OAuth configured — base_url={public_base}")

        allowed = os.getenv("MCP_ALLOWED_EMAILS")
        if allowed:
            logger.info(f"Allowed emails: {allowed}")
        else:
            logger.info("No email allowlist — any Google account can authenticate")

        return provider
    except Exception as e:
        logger.warning(f"Failed to create GoogleProvider: {e}")
        return None
