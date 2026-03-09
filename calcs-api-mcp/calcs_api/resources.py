"""MCP resources — read-only contextual data for LLMs."""


def register_resources(mcp):
    """Register MCP resources with the FastMCP instance."""

    @mcp.resource("calcs://glossary")
    async def glossary() -> str:
        """Glossary of Calcs API data formats, field meanings, and conventions."""
        return GLOSSARY_TEXT

    @mcp.resource("calcs://workflow-guide")
    async def workflow_guide() -> str:
        """Recommended tool workflows for common retail analytics tasks."""
        return WORKFLOW_GUIDE_TEXT


GLOSSARY_TEXT = """# Calcs API Glossary

## Data Format Conventions

### Test Results (from get_test_results, get_test_summary)
- **out_lift**: Cumulative lift values as a time-series array, in BASIS POINTS.
  Divide by 100 for percentage. Example: 215 = 2.15% lift.
  Each element = one week. Use [-1] (last element) for the final/current value.
- **out_confidence**: Cumulative confidence as a time-series array, in BASIS POINTS.
  Divide by 100 for percentage. Example: 9968 = 99.68% confidence.
- **out_numeric_lift**: Absolute lift values (dollars, units, etc.) as a time-series array.
- **get_test_summary** returns lift and confidence already converted to percentages.

### Significance
- A result is **statistically significant** when confidence >= 95%.
- confidence >= 90% is sometimes used as a lower threshold.
- confidence < 90% means "no signal" — the observed lift could be random noise.

### is_incomplete
- When True, the test or analysis is still running. Results are PARTIAL and may change.
- Do NOT present partial results as final conclusions.
- Check weeks_of_data or actual_test_weeks to understand how much data is available.

### filter_type Values (for get_test_results)
- **OVERALL**: All sites aggregated. NOTE: still returns per-site time-series data,
  NOT a single aggregate number. Use get_test_summary for a compact view.
- **CUSTOMER_COHORT**: Results split by customer cohort (new vs returning, etc.)
- **CUSTOMER_SEGMENT**: Results split by customer segment
- **SITE_COHORT**: Results split by site cohort (geography, format, etc.)
- **SITE_PAIR**: Results for individual treatment/control site pairs
- **FINISHED_COHORT**: Results for cohorts whose measurement is complete
- **SITE_TAG**: Results split by site tag

### Analysis Results (from Rollout Analyzer)
- **lift**: Percentage lift (already a percentage, NOT basis points)
- **confidence**: Percentage confidence (already a percentage)
- **actual_test_weeks**: Number of weeks with actual data
- **measurementLength**: Total requested measurement weeks

### Multi-Tenancy
- Most tools accept an optional `client` parameter to override the default client.
- Use get_active_clients to see which client values are available.

### Test Statuses (calcs_status)
- **PENDING**: Test created but calculations not started
- **IN_PROGRESS**: Calculations are running
- **COMPLETE**: All calculations finished
- **FAILED**: Calculations encountered an error
"""


WORKFLOW_GUIDE_TEXT = """# Recommended Workflows

## "Were the last N test results good?"
1. get_recent_tests(count=N, status="COMPLETE")  → get test IDs
2. get_test_summary(test_id=ID) for each  → compact lift/confidence/verdict

## "How did test X perform?"
1. get_test_summary(test_id=X)  → quick overview
2. If you need detail: get_test_results(test_id=X, filter_type="SITE_PAIR", summary_only=False)

## "Compare recent rollout analyses"
1. get_recent_analysis_results(count=N, run_if_needed=True)  → all in one call

## "Show me analysis results for X"
1. get_analysis_with_results(analysis_id=X, run_if_needed=True)  → config + results in one call

## "Which stores drove the lift?"
1. get_test_summary(test_id=X)  → confirm overall lift
2. get_site_pair_lift_manifest(test_id=X)  → per-pair breakdown

## "How did different customer segments respond?"
1. get_test_results(test_id=X, filter_type="CUSTOMER_COHORT")  → cohort-level results

## "What's the data freshness / history range?"
1. get_oldest_job_date()  → earliest available data
2. get_newest_job_date()  → most recent data

## General Tips
- Always start with summary/compact tools before requesting full data.
- Use search_tools(query="keyword") to discover available tools.
- Check is_incomplete before reporting results as final.
- The `client` parameter on any tool overrides the default client.
"""
