"""Test management tools."""

import json

from fastmcp import Context

from . import get_mcp
from ..summarizers import summarize_tests_list, smart_truncate_response

mcp = get_mcp()


@mcp.tool()
async def health_check(ctx: Context) -> str:
    """Check the health of the Calcs API connection.

    Returns: {"status": "healthy"} or {"status": "error", "error": "..."}.
    Use this to verify API connectivity before other operations.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.health_check()
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_tests(
    ctx: Context,
    client: str = None,
    sort_by: str = "calcs_ended",
    limit: int = 20,
    status: str = None,
    filter_keywords: list[str] = None,
) -> str:
    """Get tests with server-side sorting, filtering, and compaction.

    Returns a compact list with only essential fields (id, name, status, dates).
    Use get_recent_tests for a simpler "last N" query.

    Args:
        client: Override default client identifier.
        sort_by: Sort field — "calcs_ended" (default), "date_created", "date_updated", "test_name", "calcs_status".
        limit: Max tests to return (default 20). Set to 0 for all.
        status: Filter by calcs_status — "COMPLETE", "IN_PROGRESS", "PENDING", etc. None for all.
        filter_keywords: Extract only fields matching these keywords from raw response.
    """
    api = ctx.lifespan_context["api_client"]
    response = await api.get_tests(client or "")

    if response["status"] == "error":
        return json.dumps(response, indent=2)

    data = response["data"]

    # If keyword filtering requested, use raw filtering
    if filter_keywords:
        managed = smart_truncate_response(data, filter_keywords)
        return json.dumps({"status": "success", **managed}, indent=2)

    # Default: return compact sorted list
    effective_limit = limit if limit > 0 else 9999
    summary = summarize_tests_list(data, sort_by=sort_by, limit=effective_limit, status_filter=status)
    return json.dumps({"status": "success", **summary}, indent=2)


@mcp.tool()
async def get_recent_tests(
    ctx: Context,
    count: int = 5,
    status: str = "COMPLETE",
    client: str = None,
) -> str:
    """Get the N most recently completed tests, sorted by completion date.

    This is the recommended tool when asked "what are the recent/latest tests?"
    Returns compact records: id, name, status, dates only. No time-series data.

    Args:
        count: Number of tests to return (default 5).
        status: Filter by status — "COMPLETE" (default), "IN_PROGRESS", or None for all statuses.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]
    response = await api.get_tests(client or "")

    if response["status"] == "error":
        return json.dumps(response, indent=2)

    summary = summarize_tests_list(
        response["data"],
        sort_by="calcs_ended",
        limit=count,
        status_filter=status,
    )
    return json.dumps({"status": "success", **summary}, indent=2)


@mcp.tool()
async def get_test_status(
    ctx: Context,
    test_id: int,
    client: str = None,
) -> str:
    """Get the calculation status of a specific test.

    Returns status details including calcs_status, progress, and timing.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_test_status(test_id, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_active_clients(ctx: Context, client: str = None) -> str:
    """Get list of all active client identifiers.

    Use this to discover which client values can be passed to other tools.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_active_clients(client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_site_tests(
    ctx: Context,
    client_site_id: str,
    client: str = None,
) -> str:
    """Get all tests where a specific site has a treatment or control role.

    Args:
        client_site_id: The site identifier to look up.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_site_tests(client_site_id, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def describe_transactions(ctx: Context, client: str = None) -> str:
    """Get a descriptive overview of the fact_transactions table schema.

    Returns column names, types, and descriptions for the transaction data.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.describe_transactions(client or "")
    return json.dumps(result, indent=2)
