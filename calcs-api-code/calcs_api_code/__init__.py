"""
Calcs API Code Client

A direct Python client for the Calcs API, designed for code execution patterns.
Works with Claude Code CLI, Gemini code_execution, and any Python environment.

Quick Start:
    from calcs_api_code import CalcsClient

    client = CalcsClient(client="RetailCorp")
    tests = client.get_tests()
    active = [t for t in tests if t["status"] == "active"]
    print(f"Found {len(active)} active tests")

Environment Variables:
    CALCS_API_TOKEN: Bearer token for authentication (required)
    CALCS_API_BASE_URL: API base URL (optional, defaults to staging)
    CALCS_DEFAULT_CLIENT: Default client identifier (optional)
"""

from calcs_api_code.client import CalcsClient
from calcs_api_code.discovery import get_function_help, list_available_functions

__all__ = ["CalcsClient", "list_available_functions", "get_function_help"]
__version__ = "0.1.0"
