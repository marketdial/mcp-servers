#!/usr/bin/env python3
"""
Example: Using calcs_api_code with Claude Code CLI

When using Claude Code, you can simply write and execute Python code
that imports this package. Claude will run it in your terminal.

This file shows example patterns that Claude might generate.
"""

from collections import Counter

from calcs_api_code import CalcsClient, get_function_help, list_available_functions


def example_basic_usage():
    """Basic usage pattern."""
    client = CalcsClient(client="RetailCorp")

    # Get all tests
    tests = client.get_tests()
    print(f"Total tests: {len(tests)}")

    # Filter locally - data stays in Python, not in LLM context
    active = [t for t in tests if t.get("status") == "active"]
    print(f"Active tests: {len(active)}")


def example_data_analysis():
    """More complex data analysis pattern."""
    client = CalcsClient(client="RetailCorp")

    tests = client.get_tests()

    # Group by status
    status_counts = Counter(t.get("status", "unknown") for t in tests)
    print("Tests by status:")
    for status, count in status_counts.most_common():
        print(f"  {status}: {count}")

    # Find tests by name pattern
    pricing_tests = [t for t in tests if "pricing" in t.get("name", "").lower()]
    print(f"\nTests with 'pricing' in name: {len(pricing_tests)}")
    for t in pricing_tests[:5]:
        print(f"  - {t.get('name')}")


def example_progressive_discovery():
    """Discover available functions without loading all definitions."""
    # List what's available
    functions = list_available_functions()
    print(f"Available functions: {functions}")

    # Get help for a specific function
    help_text = get_function_help("get_tests")
    print(f"\nHelp for get_tests:\n{help_text}")


def example_with_context_manager():
    """Using the client as a context manager."""
    with CalcsClient(client="RetailCorp") as client:
        health = client.health_check()
        print(f"API health: {health}")

        tests = client.get_tests()
        print(f"Found {len(tests)} tests")
    # Connection automatically closed


def example_multi_client():
    """Working with multiple clients."""
    # Get list of clients first
    client = CalcsClient()  # Uses default or no client
    clients = client.get_active_clients()
    print(f"Active clients: {[c.get('name') for c in clients[:5]]}")

    # Query specific client
    for c in clients[:2]:
        client_name = c.get("name")
        tests = client.get_tests(client=client_name)
        print(f"{client_name}: {len(tests)} tests")


if __name__ == "__main__":
    print("=== Basic Usage ===")
    example_basic_usage()

    print("\n=== Data Analysis ===")
    example_data_analysis()

    print("\n=== Progressive Discovery ===")
    example_progressive_discovery()
