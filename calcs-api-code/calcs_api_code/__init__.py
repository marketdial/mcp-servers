"""
Calcs API Code Client

A direct Python client for the Calcs API, designed for code execution patterns.
Works with Claude Code CLI, Gemini code_execution, and any Python environment.

Quick Start - API Client:
    from calcs_api_code import CalcsClient

    client = CalcsClient(client="RetailCorp")
    tests = client.get_tests()
    active = [t for t in tests if t["status"] == "active"]
    print(f"Found {len(active)} active tests")

Quick Start - Test Creation:
    from calcs_api_code import TestBuilder

    builder = TestBuilder(client="RetailCorp")
    builder.set_name("Q1 Promotion Test")
    builder.set_description("Testing 10% discount on beverages")
    builder.set_metric("SALES")
    # ... continue with interview flow

Environment Variables:
    CALCS_API_TOKEN: Bearer token for API client (required for CalcsClient)
    CALCS_API_BASE_URL: API base URL (optional, defaults to staging)
    CALCS_DEFAULT_CLIENT: Default client identifier (optional)

    POSTGRES_HOST: Database host (required for TestBuilder)
    POSTGRES_PORT: Database port (default: 5432)
    POSTGRES_USER: Database user
    POSTGRES_PASSWORD: Database password
    POSTGRES_DATABASE: Database name

    GCP_PROJECT: Google Cloud project ID (required for BigQuery)
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
"""

from calcs_api_code.client import CalcsClient
from calcs_api_code.discovery import get_function_help, list_available_functions
from calcs_api_code.interview import TestInterview, get_system_prompt
from calcs_api_code.test_creator import TestBuilder

__all__ = [
    "CalcsClient",
    "TestBuilder",
    "TestInterview",
    "get_system_prompt",
    "list_available_functions",
    "get_function_help",
]
__version__ = "0.2.0"
