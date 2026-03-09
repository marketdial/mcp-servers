"""Rollout Analyzer tools — analysis management and results."""

import json
import logging

from fastmcp import Context

from . import get_mcp
from ..summarizers import summarize_analysis_results, smart_truncate_response

mcp = get_mcp()
logger = logging.getLogger("calcs-api.tools.analysis")


@mcp.tool()
async def list_analyses(
    ctx: Context,
    client: str = None,
    include_result_status: bool = False,
    sort_by: str = "startDate",
    limit: int = 20,
) -> str:
    """List rollout analyses with optional result status check.

    Returns analysis configs with name, description, dates, and measurement length.

    Args:
        client: Override default client identifier.
        include_result_status: If True, checks each analysis for cached results and adds
            has_cached_results (bool) to each entry. Costs one extra API call per analysis
            but eliminates guessing which analyses have been run.
        sort_by: Sort field — "startDate" (default), "name", "measurementLength".
        limit: Max analyses to return (default 20). Set to 0 for all.
    """
    api = ctx.lifespan_context["api_client"]
    response = await api.list_analyses(client or "")

    if response["status"] == "error":
        return json.dumps(response, indent=2)

    analyses = response["data"]
    if isinstance(analyses, dict) and "data" in analyses:
        analyses = analyses["data"]

    if not isinstance(analyses, list):
        return json.dumps({"status": "success", "data": analyses}, indent=2)

    # Sort
    reverse = sort_by != "name"
    try:
        analyses = sorted(analyses, key=lambda a: a.get(sort_by) or "", reverse=reverse)
    except (TypeError, KeyError):
        pass

    # Limit
    total = len(analyses)
    if limit > 0:
        analyses = analyses[:limit]

    # Optionally check result status
    if include_result_status:
        await ctx.info(f"Checking result status for {len(analyses)} analyses...")
        for analysis in analyses:
            aid = analysis.get("id") or analysis.get("analysis_id")
            if aid:
                result = await api.get_analysis_results(aid, client or "")
                data = result.get("data", {})
                # "not_found" with "run the analysis first" means never run
                if isinstance(data, dict) and data.get("status") == "not_found":
                    analysis["has_cached_results"] = False
                elif result["status"] == "error":
                    analysis["has_cached_results"] = False
                else:
                    analysis["has_cached_results"] = True

    return json.dumps({
        "status": "success",
        "total": total,
        "returned": len(analyses),
        "analyses": analyses,
    }, indent=2)


@mcp.tool()
async def get_analysis(
    ctx: Context,
    analysis_id: str,
    client: str = None,
) -> str:
    """Get a specific analysis configuration by ID.

    Returns the analysis setup: name, description, dates, products, measurement length.
    Does NOT include results — use get_analysis_results or get_analysis_with_results for that.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_analysis(analysis_id, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_analysis_results(
    ctx: Context,
    analysis_id: str,
    client: str = None,
) -> str:
    """Get results of a previously run analysis.

    Differentiates between error states:
    - "never_run": Analysis exists but has never been computed. Use run_analysis to compute.
    - "not_found": Analysis ID does not exist.
    - "success": Results available with per-metric lift and confidence.

    Results include is_incomplete flag and actual_weeks vs requested measurement length.
    Confidence values are percentages (0-100). A metric is significant at >= 95%.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.get_analysis_results(analysis_id, client or "")

    if result["status"] == "error":
        return json.dumps(result, indent=2)

    data = result.get("data", {})

    # Differentiate "not found" from "never run"
    if isinstance(data, dict) and data.get("status") == "not_found":
        msg = data.get("message", "")
        if "run the analysis first" in msg.lower():
            return json.dumps({
                "status": "no_results",
                "reason": "never_run",
                "analysis_id": analysis_id,
                "message": "Analysis exists but has never been run. Use run_analysis or get_analysis_with_results(run_if_needed=True).",
            }, indent=2)
        return json.dumps({
            "status": "no_results",
            "reason": "not_found",
            "analysis_id": analysis_id,
            "message": "Analysis ID not found.",
        }, indent=2)

    # Summarize the results
    summary = summarize_analysis_results(data)
    return json.dumps({"status": "success", "analysis_id": analysis_id, **summary}, indent=2)


@mcp.tool()
async def get_analysis_with_results(
    ctx: Context,
    analysis_id: str,
    run_if_needed: bool = False,
    client: str = None,
) -> str:
    """Get analysis config AND results in one call.

    **This is the recommended tool for "show me analysis results."**

    If results exist, returns them immediately. If not:
    - run_if_needed=True: Runs the analysis synchronously, then returns results.
    - run_if_needed=False: Returns status indicating results don't exist yet.

    Prominently surfaces is_incomplete with actual vs requested measurement weeks.

    Args:
        analysis_id: The analysis ID (e.g., "analysis-4c1761991143").
        run_if_needed: If True and no cached results, runs the analysis synchronously.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]

    # Get analysis config
    config_response = await api.get_analysis(analysis_id, client or "")
    config = config_response.get("data", {}) if config_response["status"] == "success" else {}

    # Try to get existing results
    results_response = await api.get_analysis_results(analysis_id, client or "")
    results_data = results_response.get("data", {})

    has_results = (
        results_response["status"] == "success"
        and isinstance(results_data, dict)
        and results_data.get("status") != "not_found"
    )

    if not has_results and run_if_needed:
        await ctx.info(f"No cached results for {analysis_id}. Running analysis...")
        run_response = await api.run_analysis(analysis_id, client=client or "")
        if run_response["status"] == "success":
            results_data = run_response["data"]
            has_results = True
        else:
            return json.dumps({
                "status": "error",
                "analysis_id": analysis_id,
                "message": f"Failed to run analysis: {run_response.get('error', 'unknown error')}",
                "config": _compact_config(config),
            }, indent=2)

    if not has_results:
        return json.dumps({
            "status": "no_results",
            "reason": "never_run",
            "analysis_id": analysis_id,
            "message": "Analysis has never been run. Call with run_if_needed=True to compute results.",
            "config": _compact_config(config),
        }, indent=2)

    summary = summarize_analysis_results(results_data, analysis_config=config)
    return json.dumps({
        "status": "success",
        "analysis_id": analysis_id,
        "config": _compact_config(config),
        **summary,
    }, indent=2)


@mcp.tool()
async def get_recent_analysis_results(
    ctx: Context,
    count: int = 3,
    run_if_needed: bool = False,
    client: str = None,
) -> str:
    """Get results for the N most recent analyses in one call.

    Eliminates the multi-step list → check → run → fetch workflow.

    Args:
        count: Number of recent analyses to return (default 3).
        run_if_needed: If True, runs any unrun analyses synchronously.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]

    # List all analyses
    list_response = await api.list_analyses(client or "")
    if list_response["status"] == "error":
        return json.dumps(list_response, indent=2)

    analyses = list_response["data"]
    if isinstance(analyses, dict) and "data" in analyses:
        analyses = analyses["data"]

    if not isinstance(analyses, list):
        return json.dumps({"status": "error", "error": "Unexpected response format"}, indent=2)

    # Sort by date descending
    try:
        analyses = sorted(analyses, key=lambda a: a.get("startDate") or "", reverse=True)
    except (TypeError, KeyError):
        pass

    analyses = analyses[:count]
    results = []

    for i, analysis in enumerate(analyses):
        aid = analysis.get("id") or analysis.get("analysis_id")
        name = analysis.get("name", "Unknown")
        await ctx.report_progress(i + 1, count, f"Processing: {name}")

        if not aid:
            results.append({"name": name, "status": "error", "message": "No analysis ID"})
            continue

        # Try cached results first
        res = await api.get_analysis_results(aid, client or "")
        res_data = res.get("data", {})
        has_results = (
            res["status"] == "success"
            and isinstance(res_data, dict)
            and res_data.get("status") != "not_found"
        )

        if not has_results and run_if_needed:
            await ctx.info(f"Running analysis: {name}")
            run_res = await api.run_analysis(aid, client=client or "")
            if run_res["status"] == "success":
                res_data = run_res["data"]
                has_results = True

        if has_results:
            summary = summarize_analysis_results(res_data, analysis_config=analysis)
            results.append({
                "analysis_id": aid,
                "name": name,
                "config": _compact_config(analysis),
                **summary,
            })
        else:
            results.append({
                "analysis_id": aid,
                "name": name,
                "status": "no_results",
                "reason": "never_run",
                "config": _compact_config(analysis),
            })

    return json.dumps({"status": "success", "analyses": results}, indent=2)


@mcp.tool()
async def create_analysis(
    ctx: Context,
    analysis_data: dict,
    client: str = None,
) -> str:
    """Create a new rollout analysis.

    Args:
        analysis_data: Analysis configuration including name, description,
            startDate, measurementLength, products, etc.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.create_analysis(analysis_data, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def update_analysis(
    ctx: Context,
    analysis_id: str,
    analysis_data: dict,
    client: str = None,
) -> str:
    """Update an existing analysis configuration.

    Args:
        analysis_id: The analysis ID to update.
        analysis_data: Updated analysis configuration.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.update_analysis(analysis_id, analysis_data, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def delete_analysis(
    ctx: Context,
    analysis_id: str,
    client: str = None,
) -> str:
    """Delete an analysis.

    Args:
        analysis_id: The analysis ID to delete.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.delete_analysis(analysis_id, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def run_analysis(
    ctx: Context,
    analysis_id: str,
    force_refresh: bool = False,
    client: str = None,
) -> str:
    """Run a rollout analysis synchronously (waits for completion).

    For most use cases, prefer get_analysis_with_results(run_if_needed=True)
    which combines fetching config + results in one call.

    Args:
        analysis_id: The analysis ID to run.
        force_refresh: If True, recomputes even if cached results exist.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]
    await ctx.info(f"Running analysis {analysis_id} (this may take a minute)...")
    result = await api.run_analysis(analysis_id, force_refresh, client or "")
    return json.dumps(result, indent=2)


@mcp.tool()
async def start_analysis(
    ctx: Context,
    analysis_id: str,
    force_refresh: bool = False,
    client: str = None,
) -> str:
    """Start an analysis asynchronously (returns immediately).

    NOTE: This returns a progress_id, but there is currently no tool to poll
    progress. For interactive use, prefer run_analysis (synchronous) or
    get_analysis_with_results(run_if_needed=True).

    Use this only for fire-and-forget scenarios where you don't need immediate results.

    Args:
        analysis_id: The analysis ID to start.
        force_refresh: If True, recomputes even if cached results exist.
        client: Override default client identifier.
    """
    api = ctx.lifespan_context["api_client"]
    result = await api.start_analysis(analysis_id, force_refresh, client or "")
    return json.dumps(result, indent=2)


def _compact_config(config: dict) -> dict:
    """Extract just the essential config fields for display."""
    if not config:
        return {}
    return {
        k: config[k]
        for k in ["name", "description", "startDate", "measurementLength", "category"]
        if k in config
    }
