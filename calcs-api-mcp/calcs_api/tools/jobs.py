"""Job and system monitoring tools."""

import json

from fastmcp import Context

from . import get_mcp

mcp = get_mcp()


@mcp.tool()
async def get_jobs_summary(
    ctx: Context,
    start_date: str,
    end_date: str,
    client: str = None,
) -> str:
    """Get count of running jobs and compute hours for a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_jobs_summary(start_date, end_date, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_oldest_job_date(ctx: Context, client: str = None) -> str:
    """Get the date of the oldest job for the current client.

    Useful for understanding the available data history range.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_oldest_job_date(client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_newest_job_date(ctx: Context, client: str = None) -> str:
    """Get the date of the newest/most recent job for the current client.

    Useful for understanding how current the data is.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_newest_job_date(client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_clients_jobs_summary(
    ctx: Context,
    start_date: str,
    end_date: str,
    client: str = None,
) -> str:
    """Get job summary across all active clients for a date range.

    Returns job counts and compute hours per client. Useful for system
    monitoring and capacity planning.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_clients_jobs_summary(start_date, end_date, client or "")
    return json.dumps(result, indent=2)
