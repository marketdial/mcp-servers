"""Tool discovery and search."""

import json

from fastmcp import Context

from . import get_mcp

mcp = get_mcp()

# Tool catalog — maintained here so search_tools can work without
# introspecting the FastMCP registry (which may not expose descriptions
# in all versions). Keep in sync with actual tool registrations.
TOOL_CATALOG = [
    # Test Management
    {"name": "health_check", "category": "system", "description": "Check API connectivity"},
    {"name": "get_tests", "category": "tests", "description": "List tests with sorting, filtering, and compaction"},
    {"name": "get_recent_tests", "category": "tests", "description": "Get N most recent completed tests (compact)"},
    {"name": "get_test_status", "category": "tests", "description": "Get calculation status of a specific test"},
    {"name": "get_active_clients", "category": "tests", "description": "List active client identifiers"},
    {"name": "get_site_tests", "category": "tests", "description": "Get tests for a specific site"},
    {"name": "describe_transactions", "category": "tests", "description": "Get fact_transactions table schema"},

    # Results & Analytics
    {"name": "get_test_summary", "category": "results", "description": "Compact test results: final lift%, confidence%, verdict (RECOMMENDED)"},
    {"name": "get_test_results", "category": "results", "description": "Full test results with filter types (OVERALL, SITE_PAIR, etc.)"},
    {"name": "get_lift_explorer_results", "category": "results", "description": "Lift explorer detailed calculations"},
    {"name": "get_lift_explorer_ids", "category": "results", "description": "List valid lift explorer IDs"},
    {"name": "get_site_pair_lift_manifest", "category": "results", "description": "Lift per treatment/control site pair"},
    {"name": "get_prediction_table", "category": "results", "description": "Predicted vs actual performance"},
    {"name": "get_customer_cross", "category": "results", "description": "Customer segment cross-tabulation"},
    {"name": "download_all_test_data", "category": "results", "description": "Comprehensive chart data (large payload)"},

    # Rollout Analyzer
    {"name": "list_analyses", "category": "analysis", "description": "List rollout analyses with optional result status"},
    {"name": "get_analysis", "category": "analysis", "description": "Get analysis configuration"},
    {"name": "get_analysis_results", "category": "analysis", "description": "Get cached analysis results"},
    {"name": "get_analysis_with_results", "category": "analysis", "description": "Get analysis config + results in one call (RECOMMENDED)"},
    {"name": "get_recent_analysis_results", "category": "analysis", "description": "Get results for N most recent analyses in one call"},
    {"name": "create_analysis", "category": "analysis", "description": "Create a new rollout analysis"},
    {"name": "update_analysis", "category": "analysis", "description": "Update analysis configuration"},
    {"name": "delete_analysis", "category": "analysis", "description": "Delete an analysis"},
    {"name": "run_analysis", "category": "analysis", "description": "Run analysis synchronously"},
    {"name": "start_analysis", "category": "analysis", "description": "Start analysis asynchronously (fire-and-forget)"},

    # Jobs & Monitoring
    {"name": "get_jobs_summary", "category": "jobs", "description": "Job counts and compute hours for date range"},
    {"name": "get_oldest_job_date", "category": "jobs", "description": "Oldest job date (data history start)"},
    {"name": "get_newest_job_date", "category": "jobs", "description": "Newest job date (data freshness)"},
    {"name": "get_clients_jobs_summary", "category": "jobs", "description": "Cross-client job summary"},

    # Discovery
    {"name": "search_tools", "category": "discovery", "description": "Search available tools by keyword"},
]


@mcp.tool()
async def search_tools(ctx: Context, query: str) -> str:
    """Search available tools by keyword.

    Use this when you're not sure which tool to call. Returns matching
    tool names, categories, and descriptions.

    Examples:
        search_tools(query="results") → tools for fetching test/analysis results
        search_tools(query="recent") → tools that return recent/latest data
        search_tools(query="summary") → compact summary tools
        search_tools(query="analysis") → rollout analyzer tools

    Args:
        query: Search keyword(s) to match against tool names and descriptions.
    """
    query_lower = query.lower()
    matches = [
        t for t in TOOL_CATALOG
        if query_lower in t["name"].lower()
        or query_lower in t["description"].lower()
        or query_lower in t["category"].lower()
    ]

    if not matches:
        return json.dumps({
            "status": "success",
            "matches": [],
            "message": f"No tools matching '{query}'. Try: tests, results, analysis, jobs, summary, recent.",
            "categories": sorted(set(t["category"] for t in TOOL_CATALOG)),
        }, indent=2)

    return json.dumps({
        "status": "success",
        "query": query,
        "matches": matches,
    }, indent=2)
