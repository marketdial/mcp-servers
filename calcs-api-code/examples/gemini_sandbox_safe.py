"""
Safe Gemini Code Execution with Data Injection

Pattern: Fetch data server-side, inject into Gemini's sandbox for analysis.

Two approaches:
1. Prompt Injection (this file): Embed data as CSV in the prompt
   - Best for small-medium datasets (< few hundred rows)
   - Sandbox parses CSV with pandas/StringIO

2. File Upload: Use Vertex AI File API for larger datasets
   - Model sees it as local file path like /tmp/data.csv
   - Better for large datasets

The sandbox gets:
- Pre-fetched data as CSV text
- pandas, StringIO, standard library available
- No HTTP access, no custom packages needed

This gives you:
- Full sandbox safety (Gemini's isolated environment)
- Code execution capabilities for flexible analysis
- Your custom data from any source (Cloud SQL, APIs, etc.)
"""

import os
import csv
import io
import logging
from typing import List, Dict, Any

from calcs_api_code import CalcsClient

try:
    from google import genai
    from google.genai.types import (
        GenerateContentConfig,
        Tool,
        ToolCodeExecution,
    )
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_gemini_client():
    """Get configured Gemini client for Vertex AI."""
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai not installed")

    project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("GCP_PROJECT environment variable required")

    return genai.Client(
        vertexai=True,
        project=project_id,
        location="us-central1",
    )


def fetch_test_data(client_name: str) -> List[Dict[str, Any]]:
    """
    Fetch test data server-side using our package.
    This runs in YOUR environment (has DB/API access), not the sandbox.
    """
    client = CalcsClient(client=client_name)
    return client.get_tests()


def tests_to_csv(tests: List[Dict[str, Any]]) -> str:
    """
    Convert test data to CSV format (more token-efficient than JSON).

    Only includes fields relevant for analysis to minimize token usage.
    """
    output = io.StringIO()

    # Define fields to include (short names to save tokens)
    fieldnames = ["id", "name", "status", "calcs_status", "type", "weeks", "pre_weeks", "started", "ended"]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for t in tests:
        # Clean name to avoid CSV parsing issues (remove quotes, limit length)
        name = t.get("test_name", "")[:50].replace('"', "'").replace('\n', ' ')

        writer.writerow({
            "id": t.get("id", ""),
            "name": name,
            "status": t.get("test_status", ""),
            "calcs_status": t.get("calcs_status", ""),
            "type": t.get("test_type", ""),
            "weeks": t.get("week_count", ""),
            "pre_weeks": t.get("pre_week_count", ""),
            "started": t.get("calcs_started", "")[:19] if t.get("calcs_started") else "",
            "ended": t.get("calcs_ended", "")[:19] if t.get("calcs_ended") else "",
        })

    return output.getvalue()


def analyze_with_gemini_sandbox(
    tests: List[Dict[str, Any]],
    question: str,
    client_name: str,
) -> str:
    """
    Send pre-fetched data to Gemini's sandbox for safe analysis.

    Pattern:
    1. Convert data to CSV (token-efficient)
    2. Inject into prompt
    3. Gemini writes Python code using pandas/StringIO
    4. Code runs in isolated sandbox (safe!)
    5. Results returned as text
    """
    gemini = get_gemini_client()

    # Convert to CSV (more token-efficient than JSON)
    csv_data = tests_to_csv(tests)

    prompt = f"""You have A/B test data for retail client "{client_name}" in CSV format below.

Write and execute Python code to analyze this data and answer: {question}

Dataset:
```csv
{csv_data}
```

Column descriptions:
- id: Test identifier
- name: Test name
- status: Test status (COMPLETED, IN_PROGRESS, INCOMPLETE)
- calcs_status: Calculation status (COMPLETE or empty)
- type: Test category (Pricing, Promotion, New Product, Operations, Other)
- weeks: Measurement period in weeks
- pre_weeks: Pre-period in weeks
- started: When calculations started (ISO datetime)
- ended: When calculations ended (ISO datetime)

Requirements:
- Use pandas to parse the CSV with StringIO
- Provide clear, formatted output with print()
- Include specific numbers and percentages
- If relevant, identify any issues or recommendations
"""

    response = gemini.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=prompt,
        config=GenerateContentConfig(
            tools=[Tool(code_execution=ToolCodeExecution())],
            temperature=0.0,
        ),
    )

    # Extract full response including code execution results
    result_parts = []
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if hasattr(part, 'text') and part.text:
                result_parts.append(part.text)
            elif hasattr(part, 'executable_code') and part.executable_code:
                result_parts.append(f"\n```python\n{part.executable_code.code}\n```\n")
            elif hasattr(part, 'code_execution_result') and part.code_execution_result:
                output = part.code_execution_result.output
                if output:
                    result_parts.append(f"\n**Output:**\n```\n{output}\n```\n")

    return "\n".join(result_parts) if result_parts else response.text


# =============================================================================
# FastAPI Integration Example (copy this to your FastAPI app)
# =============================================================================

FASTAPI_EXAMPLE = '''
# Add this to your FastAPI app (e.g., in calcs-light)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import from this module (or copy the functions)
from examples.gemini_sandbox_safe import fetch_test_data, analyze_with_gemini_sandbox

app = FastAPI()

class AnalysisRequest(BaseModel):
    client: str
    question: str

@app.post("/api/v1/ai-analyst")
async def ai_analyst(request: AnalysisRequest):
    """
    AI-powered test analysis using Gemini's sandboxed code execution.

    Flow:
    1. Server fetches data using calcs_api_code (your environment)
    2. Data converted to CSV and sent to Gemini's sandbox
    3. Gemini writes and executes Python to analyze it (safe sandbox)
    4. Results returned to user
    """
    try:
        # Step 1: Fetch data (runs in YOUR environment with DB access)
        tests = fetch_test_data(request.client)

        # Step 2: Analyze in Gemini's sandbox (safe, isolated)
        answer = analyze_with_gemini_sandbox(tests, request.question, request.client)

        return {
            "client": request.client,
            "question": request.question,
            "test_count": len(tests),
            "answer": answer,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''


# =============================================================================
# Test the pattern
# =============================================================================

def test_sandbox_analysis():
    """Test the sandbox-safe analysis pattern."""

    if not GENAI_AVAILABLE:
        print("google-genai not installed. Run: pip install google-genai")
        return

    print("=" * 70)
    print("SANDBOX-SAFE GEMINI CODE EXECUTION TEST")
    print("=" * 70)

    client_name = "wingstop"

    # Step 1: Fetch data (YOUR server does this - has DB/API access)
    print(f"\n1. Fetching data for {client_name}...")
    tests = fetch_test_data(client_name)
    print(f"   Fetched {len(tests)} tests")

    # Show CSV format (what gets sent to sandbox)
    csv_preview = tests_to_csv(tests[:3])
    print(f"\n2. Data converted to CSV (first 3 rows):")
    for line in csv_preview.strip().split('\n')[:4]:
        print(f"   {line}")

    # Step 2: Analyze in Gemini's sandbox (SAFE - no network access)
    print(f"\n3. Sending to Gemini sandbox for analysis...")
    question = "What percentage of tests are in each status? Which test types are most common? Any recommendations?"

    print(f"\n   Question: {question}")
    print("\n" + "=" * 70)
    print("GEMINI SANDBOX RESPONSE:")
    print("=" * 70)

    answer = analyze_with_gemini_sandbox(tests, question, client_name)
    print(answer)


if __name__ == "__main__":
    test_sandbox_analysis()
