#!/usr/bin/env python3
"""
Example: AI-Driven Test Creation Interview

This example demonstrates how to use the TestInterview class to create
A/B tests through a conversational interview flow. This is designed to
be used by AI models (Claude, Gemini) to guide users through test creation.

The TestInterview class provides:
- Step-by-step guided creation
- Progress tracking
- Validation at each step
- Undo/reset capabilities
"""

from calcs_api_code import TestInterview, get_system_prompt


def example_full_interview():
    """Complete test creation interview flow."""
    # Initialize interview
    interview = TestInterview(client="RetailCorp")

    print("=== Starting Test Creation Interview ===\n")

    # Check initial progress
    progress = interview.progress
    print(f"Current step: {progress['current']}")
    print(f"Steps: {[s['name'] for s in progress['steps']]}\n")

    # Step 1: Basic Information
    print("--- Step 1: Basic Information ---")
    result = interview.set_basics(
        name="Q1 2025 Beverage Promotion Test",
        description="Testing 10% discount on soft drinks to increase sales volume",
        test_type="Promotion",
        metric="SALES"
    )
    print(f"Result: {result['message']}")
    print(f"Progress: {interview.progress['completed']}\n")

    # Step 2: Rollout Group
    print("--- Step 2: Rollout Group ---")
    # First, see available tags
    tags = interview.get_tags()
    print(f"Available tags: {[t['name'] for t in tags[:5]]}...")

    # Set rollout to full fleet (all testable sites)
    result = interview.set_rollout(full_fleet=True)
    print(f"Result: {result['message']}")
    print(f"Rollout size: {interview.get_rollout_count()} sites\n")

    # Step 3: Product Selection
    print("--- Step 3: Product Selection ---")
    # Search for products
    products = interview.search_products("beverage")
    print(f"Found products: {[p['name'] for p in products[:5]]}...")

    result = interview.set_products(hierarchy_search="soft drink")
    print(f"Result: {result['message']}\n")

    # Step 4: Sample Optimization
    print("--- Step 4: Sample Optimization ---")
    # Run optimization
    opt_result = interview.optimize_sample(target_sites=30)
    if opt_result["success"]:
        print(f"Treatment sites: {opt_result['treatment_count']}")
        print(f"Representativeness: {opt_result['representativeness']}%")
        print(f"Comparability: {opt_result['comparability']}%")

        # Accept the sample
        accept_result = interview.accept_sample()
        print(f"Result: {accept_result['message']}\n")
    else:
        print(f"Optimization failed: {opt_result['message']}\n")
        return

    # Step 5: Schedule & Confidence
    print("--- Step 5: Schedule & Confidence ---")
    result = interview.set_schedule(
        start_date="2025-02-03",  # Must be a Monday
        test_weeks=12,
        pre_weeks=13,
        expected_lift=5.0
    )
    print(f"Schedule: {result.get('schedule')}")
    print(f"Expected confidence: {result.get('confidence')}%")
    if result.get("recommendations"):
        print(f"Recommendations: {result['recommendations']}\n")

    # Step 6: Review & Create
    print("--- Step 6: Review & Create ---")
    summary = interview.get_summary()
    print("Test Summary:")
    print(f"  Name: {summary.get('name')}")
    print(f"  Metric: {summary.get('metric')}")
    print(f"  Treatment sites: {summary.get('treatment_count')}")
    print(f"  Test weeks: {summary.get('test_weeks')}")

    validation = interview.validate()
    print(f"\nValidation: {validation['message']}")

    if validation["valid"]:
        print("\nReady to create! (In production, call interview.finalize())")
        # result = interview.finalize()
        # print(f"Created test: {result['test_id']}")
    else:
        print(f"Errors: {validation['errors']}")


def example_with_tags():
    """Example using tag-based rollout instead of full fleet."""
    interview = TestInterview(client="RetailCorp")

    # Set basics
    interview.set_basics(
        name="Urban Stores Pricing Test",
        description="Testing price elasticity in urban locations",
        test_type="Pricing",
        metric="UNITS"
    )

    # Search for tags
    urban_tags = interview.get_tags(search="urban")
    print(f"Urban tags found: {urban_tags}")

    # Set rollout with include/exclude
    if urban_tags:
        interview.set_rollout(
            include_tags=[t["id"] for t in urban_tags],
            exclude_tags=[]  # Could exclude certain tags
        )
        print(f"Rollout count: {interview.get_rollout_count()}")


def example_progress_tracking():
    """Example showing progress tracking capabilities."""
    interview = TestInterview(client="RetailCorp")

    # Progress before any steps
    print("Initial progress:")
    for step in interview.progress["steps"]:
        status = "✓" if step["completed"] else "○"
        print(f"  {status} {step['name']}")

    # After setting basics
    interview.set_basics(
        name="Progress Demo Test",
        description="Demo of progress tracking",
        test_type="General",
        metric="SALES"
    )

    print("\nAfter basics:")
    for step in interview.progress["steps"]:
        status = "✓" if step["completed"] else "○"
        current = " ← current" if step["id"] == interview.progress["current"] else ""
        print(f"  {status} {step['name']}{current}")


def example_system_prompt():
    """Get the system prompt for AI models."""
    prompt = get_system_prompt()
    print("System prompt length:", len(prompt), "characters")
    print("\nFirst 500 characters:")
    print(prompt[:500])


if __name__ == "__main__":
    print("=== Full Interview Flow ===\n")
    # Note: These examples require database connection
    # example_full_interview()

    print("\n=== System Prompt ===\n")
    example_system_prompt()
