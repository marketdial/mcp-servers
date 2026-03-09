"""Results and analytics tools."""

import json

from fastmcp import Context

from . import get_mcp
from ..summarizers import summarize_test_results, smart_truncate_response

mcp = get_mcp()


@mcp.tool()
async def get_test_summary(
    ctx: Context,
    test_id: int,
    client: str = None,
) -> str:
    """Get a compact summary of a test's results: final lift, confidence, significance, and verdict.

    **This is the recommended first tool when asked about test performance.**
    Returns ~300 tokens instead of 225k+ characters.

    Lift and confidence are returned as PERCENTAGES (the raw API uses basis points
    internally — this tool handles the conversion).

    A test is flagged as "significant" when confidence >= 95%.
    If the test is still running, is_incomplete=true is prominently surfaced.

    Args:
        test_id: The numeric test ID.
        client: Override default client identifier.

    Returns:
        JSON with: test_id, is_incomplete, metrics (per-metric lift_pct, confidence_pct,
        significant, weeks_of_data), and a human-readable verdict string.
    """
    api = ctx.lifespan_context["api_client"]
    response = await api.get_test_results(test_id, "OVERALL", client=client or "")

    if response["status"] == "error":
        return json.dumps(response, indent=2)

    summary = summarize_test_results(response["data"])
    summary["test_id"] = test_id
    return json.dumps({"status": "success", **summary}, indent=2)


@mcp.tool()
async def get_test_results(
    ctx: Context,
    test_id: int,
    filter_type: str,
    filter_value: str = None,
    summary_only: bool = True,
    client: str = None,
    filter_keywords: list[str] = None,
) -> str:
    """Get test results with filtering. Defaults to returning a compact summary.

    filter_type controls the data slice:
    - OVERALL: All sites aggregated (still returns per-site time-series — use get_test_summary for a compact view)
    - CUSTOMER_COHORT: Results split by customer cohort
    - CUSTOMER_SEGMENT: Results split by customer segment
    - SITE_COHORT: Results split by site cohort
    - SITE_PAIR: Results for individual site pairs
    - FINISHED_COHORT: Results for finished cohorts only
    - SITE_TAG: Results split by site tag

    RAW DATA FORMAT (when summary_only=False):
    - out_lift: Array of cumulative lift values in BASIS POINTS (divide by 100 for %)
    - out_confidence: Array of cumulative confidence in BASIS POINTS (divide by 100 for %)
    - out_numeric_lift: Array of absolute lift values (dollars/units)
    - Each array element = one week of data; use [-1] for the final/current value

    Args:
        test_id: The numeric test ID.
        filter_type: One of OVERALL, CUSTOMER_COHORT, CUSTOMER_SEGMENT, SITE_COHORT, SITE_PAIR, FINISHED_COHORT, SITE_TAG.
        filter_value: Required for some filter types (e.g., specific cohort name).
        summary_only: If True (default), returns compact summary with final values only.
            Set to False for full time-series data.
        client: Override default client identifier.
        filter_keywords: When summary_only=False, extract only fields matching these keywords.
    """
    api = ctx.lifespan_context["api_client"]
    response = await api.get_test_results(test_id, filter_type, filter_value, client or "")

    if response["status"] == "error":
        return json.dumps(response, indent=2)

    if summary_only:
        summary = summarize_test_results(response["data"])
        summary["test_id"] = test_id
        summary["filter_type"] = filter_type
        return json.dumps({"status": "success", **summary}, indent=2)

    # Full data mode — apply truncation/filtering
    managed = smart_truncate_response(response["data"], filter_keywords)
    return json.dumps({"status": "success", **managed}, indent=2)


@mcp.tool()
async def get_lift_explorer_results(
    ctx: Context,
    lift_explorer_id: str,
    client: str = None,
    filter_keywords: list[str] = None,
) -> str:
    """Get lift explorer results (JSON equivalent of .avro file contents).

    These are detailed lift calculations. Use filter_keywords to extract
    specific fields if the response is too large.

    Args:
        lift_explorer_id: The lift explorer ID.
        client: Override default client identifier.
        filter_keywords: Extract only fields matching these keywords.
    """
    api = ctx.lifespan_context["api_client"]
    response = await api.get_lift_explorer_results(lift_explorer_id, client or "")

    if response["status"] == "error":
        return json.dumps(response, indent=2)

    managed = smart_truncate_response(response["data"], filter_keywords)
    return json.dumps({"status": "success", **managed}, indent=2)


@mcp.tool()
async def get_lift_explorer_ids(ctx: Context, client: str = None) -> str:
    """Get list of valid lift explorer IDs for the current client.

    Use these IDs with get_lift_explorer_results.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_lift_explorer_ids(client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_site_pair_lift_manifest(
    ctx: Context,
    test_id: int,
    client: str = None,
) -> str:
    """Get the site pair lift manifest — shows lift per treatment/control site pair.

    Useful for understanding which specific store pairs drove the overall result.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_site_pair_lift_manifest(test_id, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_prediction_table(
    ctx: Context,
    test_id: int,
    client: str = None,
) -> str:
    """Get prediction table data for a test.

    Shows predicted vs actual performance projections.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_prediction_table(test_id, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_customer_cross(
    ctx: Context,
    test_id: int,
    client: str = None,
) -> str:
    """Get customer cross-tabulation data for a test.

    Shows how different customer segments responded to the test intervention.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_customer_cross(test_id, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def download_all_test_data(
    ctx: Context,
    test_id: int,
    client: str = None,
    filter_keywords: list[str] = None,
) -> str:
    """Download comprehensive chart data for a test.

    WARNING: This returns a large payload. Use filter_keywords to extract
    specific fields, or prefer get_test_summary for a compact overview.

    Args:
        test_id: The numeric test ID.
        client: Override default client identifier.
        filter_keywords: Extract only fields matching these keywords.
    """
    api = ctx.lifespan_context["api_client"]
    response = await api.download_all_test_data(test_id, client or "")

    if response["status"] == "error":
        return json.dumps(response, indent=2)

    managed = smart_truncate_response(response["data"], filter_keywords)
    return json.dumps({"status": "success", **managed}, indent=2)
