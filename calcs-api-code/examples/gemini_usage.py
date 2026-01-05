#!/usr/bin/env python3
"""
Example: Using calcs_api_code with Gemini Code Execution

This demonstrates how to use the Calcs API client with Gemini 2.0+
code execution capabilities via the google-genai SDK.

Requirements:
    pip install google-genai

Setup:
    - Ensure you have GCP credentials configured
    - The calcs_api_code package must be installed in the execution environment
"""

import os

# Check if google-genai is available
try:
    from google import genai
    from google.genai.types import GenerateContentConfig, Tool, ToolCodeExecution

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("google-genai not installed. Run: pip install google-genai")


def create_gemini_client(project_id: str, location: str = "us-central1"):
    """
    Create a Gemini client configured for Vertex AI.

    Args:
        project_id: Your GCP project ID
        location: GCP region (default: us-central1)

    Returns:
        Configured genai.Client
    """
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai package not installed")

    return genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )


def ask_about_tests(
    client, question: str, retail_client: str = "RetailCorp"
) -> str:
    """
    Use Gemini with code execution to answer questions about tests.

    The model will write Python code using the calcs_api_code package,
    execute it, and return a summary of the results.

    Args:
        client: The genai.Client instance
        question: Natural language question about tests
        retail_client: The retail client to query

    Returns:
        Gemini's response with the answer
    """
    system_prompt = f"""
You have access to the calcs_api_code Python package for querying retail test data.

Example usage:
```python
from calcs_api_code import CalcsClient

client = CalcsClient(client="{retail_client}")
tests = client.get_tests()
active = [t for t in tests if t["status"] == "active"]
print(f"Found {{len(active)}} active tests")
```

Available methods:
- get_tests(client?) - Get all tests
- get_test_status(test_id, client?) - Get status of specific test
- get_active_clients(client?) - List all clients
- get_site_tests(client_site_id, client?) - Get tests for a site
- get_test_results(test_id, filter_type?, filter_value?, client?) - Get test results
- list_analyses(client?) - List rollout analyses

Write Python code to answer the user's question, execute it, and summarize the results.
Process data locally (filtering, aggregation) rather than returning raw data.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=question,
        config=GenerateContentConfig(
            tools=[Tool(code_execution=ToolCodeExecution())],
            system_instruction=system_prompt,
            temperature=0.0,  # Lower temperature for more consistent code
        ),
    )

    return response.text


def example_questions():
    """Example questions that work well with this pattern."""
    return [
        "How many active tests does RetailCorp have?",
        "What are the most common test statuses?",
        "List the 5 most recent tests by name",
        "How many tests are in progress vs completed?",
        "Which sites have the most tests?",
    ]


def main():
    """Run example Gemini queries."""
    if not GENAI_AVAILABLE:
        print("Cannot run example: google-genai not installed")
        return

    # Get project ID from environment or prompt
    project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("Set GCP_PROJECT or GOOGLE_CLOUD_PROJECT environment variable")
        return

    print(f"Using GCP project: {project_id}")

    # Create client
    client = create_gemini_client(project_id)

    # Ask a question
    question = "How many active tests does RetailCorp have?"
    print(f"\nQuestion: {question}")

    try:
        answer = ask_about_tests(client, question)
        print(f"\nAnswer: {answer}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
