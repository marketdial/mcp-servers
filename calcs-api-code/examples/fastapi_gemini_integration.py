"""
FastAPI + Gemini Code Execution Integration

Two approaches for using calcs_api_code with Gemini in a FastAPI server:

1. HYBRID APPROACH (Recommended): Gemini generates code, your server executes it
   - Full control over execution environment
   - Package is definitely available
   - Can add safety checks

2. NATIVE CODE EXECUTION: Gemini runs code in its sandbox
   - Simpler but sandbox may not have your package
   - Good for standard library / common packages only
"""

import os
import json
import logging
from typing import Optional
from contextlib import redirect_stdout
import io

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Check for google-genai
try:
    from google import genai
    from google.genai.types import (
        GenerateContentConfig,
        Tool,
        ToolCodeExecution,
        Part,
        Content,
    )
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

app = FastAPI(title="Calcs AI Analyst")


# =============================================================================
# APPROACH 1: HYBRID - Gemini generates code, you execute it (RECOMMENDED)
# =============================================================================

class AnalysisRequest(BaseModel):
    client: str
    question: str


class AnalysisResponse(BaseModel):
    question: str
    answer: str
    code_executed: Optional[str] = None


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
        location="us-central1",  # or "global" for some models
    )


def generate_analysis_code(gemini_client, question: str, retail_client: str) -> str:
    """
    Ask Gemini to generate Python code that answers the question.
    Returns the code string (not executed yet).
    """

    system_prompt = f"""You are a Python code generator for retail A/B test analysis.

You have access to the calcs_api_code package. Here's how to use it:

```python
from calcs_api_code import CalcsClient
from collections import Counter
from datetime import datetime

client = CalcsClient(client='{retail_client}')
tests = client.get_tests()  # Returns list of test dicts

# Each test has fields like:
# - id, test_name, test_description
# - test_status: COMPLETED, IN_PROGRESS, INCOMPLETE
# - calcs_status: COMPLETE, None
# - test_type: Pricing, Promotion, New Product, Operations, Other
# - week_count, pre_week_count
# - calcs_started, calcs_ended (ISO datetime strings)
```

Generate Python code that:
1. Fetches the test data
2. Analyzes it to answer the user's question
3. Prints a clear, formatted answer

IMPORTANT:
- Output ONLY the Python code, no markdown, no explanation
- Use print() for all output
- Handle edge cases (empty data, missing fields)
- Format output for human readability
"""

    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=f"Generate Python code to answer: {question}",
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.0,
        ),
    )

    code = response.text.strip()

    # Clean up markdown if present
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]

    return code.strip()


def execute_analysis_code(code: str) -> str:
    """
    Execute the generated Python code in a controlled environment.
    Returns the captured stdout.
    """
    # Capture stdout
    stdout_capture = io.StringIO()

    # Create a restricted globals dict
    # Only allow safe imports
    safe_globals = {
        "__builtins__": {
            "print": print,
            "len": len,
            "sum": sum,
            "min": min,
            "max": max,
            "sorted": sorted,
            "list": list,
            "dict": dict,
            "set": set,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "any": any,
            "all": all,
            "round": round,
            "abs": abs,
            "isinstance": isinstance,
            "type": type,
            "getattr": getattr,
            "hasattr": hasattr,
            "None": None,
            "True": True,
            "False": False,
        },
        # Pre-import allowed modules
        "CalcsClient": __import__("calcs_api_code").CalcsClient,
        "Counter": __import__("collections").Counter,
        "defaultdict": __import__("collections").defaultdict,
        "datetime": __import__("datetime").datetime,
        "timedelta": __import__("datetime").timedelta,
        "statistics": __import__("statistics"),
    }

    try:
        with redirect_stdout(stdout_capture):
            exec(code, safe_globals)
        return stdout_capture.getvalue()
    except Exception as e:
        return f"Error executing analysis: {type(e).__name__}: {e}"


@app.post("/api/v1/ai-analyst", response_model=AnalysisResponse)
async def ai_analyst(request: AnalysisRequest):
    """
    AI-powered test analysis endpoint.

    Gemini generates Python code to answer the question,
    then we execute it with access to calcs_api_code.
    """
    try:
        gemini = get_gemini_client()

        # Step 1: Generate code
        code = generate_analysis_code(gemini, request.question, request.client)
        logger.info(f"Generated code for: {request.question}")

        # Step 2: Execute code
        result = execute_analysis_code(code)

        return AnalysisResponse(
            question=request.question,
            answer=result,
            code_executed=code,
        )

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# APPROACH 2: Pre-built analysis functions (No code generation)
# =============================================================================

@app.get("/api/v1/test-report/{client}")
async def get_test_report(client: str):
    """
    Pre-built comprehensive test report.
    No AI needed - just runs the analysis directly.
    """
    from calcs_api_code import CalcsClient
    from collections import Counter
    from datetime import datetime

    api_client = CalcsClient(client=client)
    tests = api_client.get_tests()

    # Compute metrics
    by_status = Counter(t.get('test_status') for t in tests)
    by_type = Counter(t.get('test_type') for t in tests)

    week_counts = [t.get('week_count', 0) for t in tests if t.get('week_count')]
    avg_weeks = sum(week_counts) / len(week_counts) if week_counts else 0

    completed = len([t for t in tests if t.get('test_status') == 'COMPLETED'])
    in_progress = len([t for t in tests if t.get('test_status') == 'IN_PROGRESS'])

    return {
        "client": client,
        "summary": {
            "total_tests": len(tests),
            "completed": completed,
            "in_progress": in_progress,
            "completion_rate": f"{completed * 100 // len(tests)}%" if tests else "0%",
        },
        "by_status": dict(by_status),
        "by_type": dict(by_type),
        "timing": {
            "avg_measurement_weeks": round(avg_weeks, 1),
            "max_weeks": max(week_counts) if week_counts else 0,
        },
    }


# =============================================================================
# APPROACH 3: Native Gemini Code Execution (if sandbox has dependencies)
# =============================================================================

@app.post("/api/v1/ai-analyst-native")
async def ai_analyst_native(request: AnalysisRequest):
    """
    Uses Gemini's native code execution.

    NOTE: This only works if Gemini's sandbox has access to calcs_api_code,
    which it typically won't for custom packages. Use approach 1 instead.

    This is here for reference / if using only standard library.
    """
    gemini = get_gemini_client()

    system_prompt = f"""You have access to the calcs_api_code Python package.

from calcs_api_code import CalcsClient
client = CalcsClient(client='{request.client}')
tests = client.get_tests()

Write and execute Python code to answer the user's question.
Process the data and provide a clear summary."""

    response = gemini.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=request.question,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[Tool(code_execution=ToolCodeExecution())],
            temperature=0.0,
        ),
    )

    return {
        "question": request.question,
        "answer": response.text,
    }


# =============================================================================
# Example usage
# =============================================================================

if __name__ == "__main__":
    # Test the hybrid approach locally
    import asyncio

    async def test():
        request = AnalysisRequest(
            client="wingstop",
            question="How many tests are in progress and what types are they?"
        )

        result = await ai_analyst(request)
        print("Question:", result.question)
        print("\nGenerated Code:")
        print(result.code_executed)
        print("\nAnswer:")
        print(result.answer)

    asyncio.run(test())
