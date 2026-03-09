"""MCP prompt templates for common retail analytics workflows."""


def register_prompts(mcp):
    """Register MCP prompts with the FastMCP instance."""

    @mcp.prompt()
    async def analyze_test(test_id: int) -> list:
        """Analyze a test's performance — start with summary, then drill into details if significant."""
        return [
            {
                "role": "user",
                "content": (
                    f"Analyze the results for test {test_id}.\n\n"
                    "1. First call get_test_summary to get the high-level metrics.\n"
                    "2. Report the lift, confidence, and significance for each metric.\n"
                    "3. If the test is incomplete, clearly note that results are partial.\n"
                    "4. If results are significant, offer to drill into site-pair or "
                    "customer-cohort breakdowns for deeper insight."
                ),
            }
        ]

    @mcp.prompt()
    async def compare_recent_tests(count: int = 3) -> list:
        """Compare the N most recent completed tests."""
        return [
            {
                "role": "user",
                "content": (
                    f"Compare the {count} most recently completed tests.\n\n"
                    f"1. Call get_recent_tests(count={count}, status='COMPLETE').\n"
                    "2. For each test, call get_test_summary to get results.\n"
                    "3. Present a comparison table: test name, lift%, confidence%, verdict.\n"
                    "4. Rank them by lift magnitude and note which are significant."
                ),
            }
        ]

    @mcp.prompt()
    async def rollout_review(count: int = 3) -> list:
        """Review the most recent rollout analyses."""
        return [
            {
                "role": "user",
                "content": (
                    f"Review the {count} most recent rollout analyses.\n\n"
                    f"1. Call get_recent_analysis_results(count={count}, run_if_needed=True).\n"
                    "2. For each analysis, report: name, category, lift%, confidence%, and verdict.\n"
                    "3. Flag any incomplete analyses prominently (actual vs requested weeks).\n"
                    "4. Summarize: which rollouts show positive signal, which don't?"
                ),
            }
        ]
