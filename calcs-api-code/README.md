# Calcs API Code Client

Direct Python client for the Calcs API, designed for code execution patterns.
Works with Claude Code CLI, Gemini `code_execution`, and any Python environment.

## Quick Start

### Query Tests

```python
from calcs_api_code import CalcsClient

client = CalcsClient(client="RetailCorp")
tests = client.get_tests()
active = [t for t in tests if t["status"] == "active"]
print(f"Found {len(active)} active tests")
```

### Create Tests (AI Interview)

```python
from calcs_api_code import TestInterview

interview = TestInterview(client="RetailCorp")

# Step 1: Basic info
interview.set_basics(
    name="Q1 Promo Test",
    description="Testing 10% discount on beverages",
    test_type="Promotion",
    metric="SALES"
)

# Step 2: Rollout group
interview.set_rollout(include_tags=[1, 2])

# Step 3: Products
interview.set_products(hierarchy_search="beverages")

# Step 4: Sample optimization
interview.optimize_and_accept(target_sites=30)

# Step 5: Schedule
interview.set_schedule("2025-02-03", test_weeks=12)

# Step 6: Create
result = interview.finalize()
print(f"Created test: {result['test_id']}")
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

# Required for test creation (TestBuilder/TestInterview):
# Option 1: Use secrets/configs/staging.config.json (preferred)
# The library will auto-detect this file and use client-specific credentials

# Option 2: Use environment variables (fallback)
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=5432
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=your_database

# Required for sample optimization metrics:
GCP_PROJECT=your_gcp_project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Config File Auto-Detection

When using `TestBuilder` or `TestInterview` with a client name, the library automatically looks for credentials in:

1. `../secrets/configs/staging.config.json` (relative to package)
2. `/Users/jeff/Code/mcp-servers/secrets/configs/staging.config.json`

```python
from calcs_api_code.db import list_available_clients

# See which clients are configured
clients = list_available_clients()
print(clients)  # ['maverik', 'dicks', 'potbelly', ...]

# TestInterview automatically uses the right database for each client
from calcs_api_code import TestInterview
interview = TestInterview(client="maverik")  # Uses maverik's database
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

### Test Creation (TestInterview)

High-level API for AI-driven test creation:

| Method | Description |
|--------|-------------|
| `set_basics(name, description, test_type, metric)` | Set basic test information |
| `set_rollout(include_tags?, exclude_tags?, full_fleet?)` | Define rollout group |
| `set_products(hierarchy_ids?, hierarchy_search?)` | Select products/categories |
| `optimize_sample(target_sites)` | Run sample optimization |
| `accept_sample()` | Accept the optimized sample |
| `optimize_and_accept(target_sites)` | Optimize and accept in one step |
| `set_schedule(start_date, test_weeks?, pre_weeks?, expected_lift?)` | Set schedule and estimate confidence |
| `get_summary()` | Get complete test configuration summary |
| `validate()` | Check if test is ready to create |
| `finalize()` | Create the test in the database |

### Test Creation (TestBuilder - Low Level)

Step-by-step builder for full control:

| Method | Description |
|--------|-------------|
| `set_name(name)` | Set test name (validates uniqueness) |
| `set_description(description)` | Set test description |
| `set_test_type(test_type)` | Set test category |
| `set_metric(metric)` | Set primary metric |
| `get_available_tags(search?)` | List available site tags |
| `set_rollout_tags(include?, exclude?)` | Set rollout by tags |
| `search_hierarchies(search, level?)` | Search product hierarchies |
| `set_hierarchies(hierarchy_ids)` | Set product selection |
| `get_eligible_sites()` | Get sites available for treatment |
| `estimate_confidence(expected_lift)` | Estimate detection power |
| `create()` | Create the test |

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

### AI-Driven Test Creation

```python
from calcs_api_code import TestInterview, get_system_prompt

# Get the AI system prompt for test creation interviews
system_prompt = get_system_prompt()

# Create interview instance
interview = TestInterview(client="RetailCorp")

# Check progress at any time
progress = interview.progress
print(f"Current step: {progress['current']}")
print(f"Completed: {progress['completed']}")

# Step through the interview flow
interview.set_basics(
    name="Summer Sale Test",
    description="Testing 15% discount impact on beverage sales",
    test_type="Promotion",
    metric="SALES"
)

# Get available tags for rollout selection
tags = interview.get_tags(search="urban")
print(f"Found tags: {[t['name'] for t in tags]}")

# Set rollout (full fleet or by tags)
interview.set_rollout(full_fleet=True)
print(f"Rollout sites: {interview.get_rollout_count()}")

# Search and select products
products = interview.search_products("beverage")
interview.set_products(hierarchy_search="beverage")

# Optimize sample for representativeness
result = interview.optimize_sample(target_sites=30)
print(f"Representativeness: {result['representativeness']}%")
interview.accept_sample()

# Set schedule and get confidence
schedule = interview.set_schedule("2025-03-03", test_weeks=12, expected_lift=5.0)
print(f"Confidence: {schedule['confidence']}%")

# Review and finalize
summary = interview.get_summary()
validation = interview.validate()

if validation["valid"]:
    result = interview.finalize()
    print(f"Created test: {result['test_id']}")
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
