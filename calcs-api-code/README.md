# Calcs API Code Client

Direct Python client for the Calcs API, designed for code execution patterns.
Works with Claude Code CLI, Gemini `code_execution`, and any Python environment.

## Quick Start

```python
from calcs_api_code import CalcsClient

client = CalcsClient(client="RetailCorp")
tests = client.get_tests()
active = [t for t in tests if t["status"] == "active"]
print(f"Found {len(active)} active tests")
```

## Installation

```bash
# Install in development mode
cd calcs-api-code
uv pip install -e .

# Or with pip
pip install -e .
```

## Environment Variables

Set these in your environment or a `.env` file:

```bash
# Required: Bearer token for authentication
CALCS_API_TOKEN=your_token_here

# Optional: API base URL (defaults to staging)
CALCS_API_BASE_URL=https://staging-app.marketdial.dev/calcs

# Optional: Default client for multi-tenant access
CALCS_DEFAULT_CLIENT=your_client_name
```

## Available Methods

### Test Management

| Method | Description |
|--------|-------------|
| `get_tests(client?)` | Get all tests |
| `get_test_status(test_id, client?)` | Get status of a specific test |
| `get_active_clients(client?)` | List all active clients |
| `get_site_tests(client_site_id, client?)` | Get tests for a specific site |
| `health_check()` | Check API connectivity |

### Results & Analytics

| Method | Description |
|--------|-------------|
| `get_test_results(test_id, filter_type?, filter_value?, client?)` | Get test results with filtering |
| `get_lift_explorer_results(lift_explorer_id, client?)` | Get lift explorer results |

### Analysis Management

| Method | Description |
|--------|-------------|
| `list_analyses(client?)` | List all rollout analyses |
| `get_analysis(analysis_id, client?)` | Get a specific analysis |

## Usage Examples

### Filter and Analyze Tests

```python
from calcs_api_code import CalcsClient

client = CalcsClient(client="RetailCorp")

# Get all tests and filter locally (data stays in Python, not in LLM context)
tests = client.get_tests()

# Count by status
from collections import Counter
status_counts = Counter(t["status"] for t in tests)
print(f"Tests by status: {dict(status_counts)}")

# Find recent tests
recent = [t for t in tests if "2024" in t.get("created_at", "")]
print(f"Tests created in 2024: {len(recent)}")
```

### Get Test Results

```python
from calcs_api_code import CalcsClient

client = CalcsClient(client="RetailCorp")

# Get overall results for a test
results = client.get_test_results(test_id=123, filter_type="OVERALL")
print(f"Test 123 lift: {results.get('lift', 'N/A')}")
```

### Progressive Discovery

```python
from calcs_api_code import list_available_functions, get_function_help

# See what's available
functions = list_available_functions()
print(f"Available: {functions}")

# Get help for a specific function
help_text = get_function_help("get_tests")
print(help_text)
```

### Using with Gemini Code Execution

```python
from google import genai
from google.genai.types import Tool, ToolCodeExecution, GenerateContentConfig

client = genai.Client(vertexai=True, project="your-project", location="us-central1")

response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="How many active tests does RetailCorp have?",
    config=GenerateContentConfig(
        tools=[Tool(code_execution=ToolCodeExecution())],
        system_instruction="""
        You have access to the calcs_api_code Python package.
        Use it like this:

        from calcs_api_code import CalcsClient
        client = CalcsClient(client="RetailCorp")
        tests = client.get_tests()
        """,
        temperature=0.0
    )
)
print(response.text)
```

## Design Philosophy

This client follows the "Code Execution with MCP" pattern:

1. **No MCP overhead**: Instead of 26 tool definitions consuming tokens, just import and use
2. **Data stays local**: Large datasets are processed in Python, only summaries returned
3. **Full Python power**: Filter, aggregate, and transform using native Python
4. **Works everywhere**: Same code for Claude Code CLI, Gemini, or any Python environment

## Comparison with MCP Approach

| Aspect | MCP Tools | Code Execution |
|--------|-----------|----------------|
| Token overhead | ~13,000 (26 tools) | ~0 |
| Large data | Truncation needed | Process locally |
| Filtering | Fixed parameters | Native Python |
| Flexibility | Tool constraints | Full Python |
