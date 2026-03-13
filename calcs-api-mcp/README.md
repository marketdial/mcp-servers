# Calcs API MCP Server (Python / FastMCP)

A Python MCP server that gives **Claude Code**, **Cursor**, **LM Studio**, and other MCP clients access to the Calcs API for retail analytics, A/B test management, and rollout analysis. Built with [FastMCP](https://github.com/jlowin/fastmcp).

> **Note:** This is the Python rewrite of the original TypeScript `calcs-api/` server. It adds HTTP + SSE multi-transport support, smart response summarization, Google OAuth for remote clients, and convenience tools for common workflows.

---

## Quick Start

```bash
cd calcs-api-mcp

# 1. Install dependencies
uv sync

# 2. Configure authentication (see Authentication below)
cp .env.example .env
# Edit .env with your token and client

# 3. Start the server
uv run calcs-api          # stdio transport (default, for Claude Desktop/Code)
uv run calcs-api-http     # HTTP transport on port 8002 (for LM Studio, remote)
uv run calcs-api-sse      # SSE transport on port 8001 (legacy)
```

---

## Authentication

The server uses **two separate layers** of authentication:

### Layer 1: Calcs API Authentication (Required)

Every transport mode needs a bearer token to authenticate with the upstream Calcs API. Two modes are supported:

#### Option A: Auth0 Password Grant (Recommended for Deployments)

The server fetches a bearer token from Auth0 at startup and **auto-refreshes** it before expiry. This is the preferred mode for Cloud Run and other deployed environments.

```env
# .env
AUTH0_PASSWORD=your_auth0_password_here
```

The server uses a shared service account (`aqaadmin@marketdial.com`) to obtain tokens. The password is the only secret you need to store.

#### Option B: Static Bearer Token (Local Development)

For quick local development, you can provide a pre-obtained bearer token directly:

```env
# .env
CALCS_API_TOKEN=your_bearer_token_here
```

**Note:** Static tokens expire periodically and must be manually refreshed. Use Auth0 password grant for long-running deployments.

If both `AUTH0_PASSWORD` and `CALCS_API_TOKEN` are set, Auth0 takes precedence.

### Layer 2: Client Authentication (Transport-Dependent)

How *users* authenticate to the MCP server depends on which transport you use:

| Transport | Auth Method | Use Case |
|-----------|-------------|----------|
| **stdio** | None needed — inherits caller's environment | Claude Code (local) |
| **HTTP** | Google OAuth (optional) | LM Studio, remote clients |
| **SSE** | Google OAuth (optional) | Cursor, legacy clients |

#### stdio (Claude Code local)

No additional auth is needed. The MCP server runs as a subprocess of Claude Code, inheriting the environment variables (including `CALCS_API_TOKEN`) directly. This is the simplest and most secure mode.

#### HTTP / SSE with Google OAuth (Optional)

For remote/shared deployments, you can enable Google OAuth so users authenticate with their Google accounts before accessing the MCP server.

```env
# .env (add these to enable OAuth)
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
MCP_BASE_URL=http://localhost:8002   # Public URL for OAuth redirects
```

If `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are not set, OAuth is disabled and the server runs without user-level authentication (fine for local use).

**Setting up Google OAuth credentials:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create an OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URI: `{MCP_BASE_URL}/oauth/callback`
4. Copy the Client ID and Client Secret to your `.env`

### Multi-Tenant Client Header

The Calcs API is multi-tenant — every request needs a `client` header identifying which retail client's data to access.

```env
# .env
CALCS_DEFAULT_CLIENT=your_client_name    # Used when tools don't specify a client
```

You can also override per-request by passing `client="other_client"` to any tool. Use the `get_active_clients` tool to discover valid client names.

---

## Environment Variables Summary

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CALCS_API_TOKEN` | **Yes** | — | Bearer token for the Calcs API |
| `CALCS_DEFAULT_CLIENT` | Recommended | `""` | Default client identifier |
| `CALCS_API_BASE_URL` | No | `https://staging-app.marketdial.dev/calcs` | Calcs API base URL |
| `GOOGLE_CLIENT_ID` | No | — | Google OAuth client ID (HTTP/SSE only) |
| `GOOGLE_CLIENT_SECRET` | No | — | Google OAuth client secret (HTTP/SSE only) |
| `MCP_BASE_URL` | No | `http://localhost:8002` | Public base URL for OAuth redirects |

---

## Client Configuration

### Claude Code

**Option A: HTTP transport (recommended for remote server)**

Start the server, then register it:

```bash
# Start the server (in a separate terminal)
uv run calcs-api

# Register with Claude Code
claude mcp add calcs-api-http http://localhost:8002/mcp/
```

**Option B: Direct command (recommended for local use)**

No separate server process needed — Claude Code launches it as a subprocess:

```bash
claude mcp add calcs-api \
  --transport command \
  -- uv run --directory /path/to/calcs-api-mcp calcs-api
```

Or add to your Claude Code settings JSON (`~/.claude/settings.json` or project `.claude/settings.json`):

```json
{
  "mcpServers": {
    "calcs-api": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/calcs-api-mcp", "calcs-api"],
      "env": {
        "CALCS_API_TOKEN": "your_token_here",
        "CALCS_DEFAULT_CLIENT": "your_client"
      }
    }
  }
}
```

### Cursor IDE

```json
{
  "mcp": {
    "servers": {
      "calcs-api": {
        "url": "http://localhost:8002/mcp/"
      }
    }
  }
}
```

### LM Studio

```json
{
  "mcpServers": {
    "calcs-api-server": {
      "url": "http://127.0.0.1:8002/mcp/"
    }
  }
}
```

---

## Transports

| Transport | Port | Endpoint | Start Command |
|-----------|------|----------|---------------|
| stdio (Default) | — | stdin/stdout | `uv run calcs-api` or `uv run calcs-api-stdio` |
| HTTP (Streamable) | 8002 | `/mcp/` | `uv run calcs-api-http` |
| SSE (Legacy) | 8001 | `/sse/` | `uv run calcs-api-sse` |

---

## Tools (30)

### Test Management (7 tools)

| Tool | Description |
|------|-------------|
| `health_check` | Check API connectivity |
| `get_tests` | Get tests with sorting, filtering, and compaction |
| `get_recent_tests` | Get the N most recently completed tests |
| `get_test_status` | Get calculation status for a specific test |
| `get_active_clients` | List all active client identifiers |
| `get_site_tests` | Get tests involving a specific site |
| `describe_transactions` | Get fact_transactions table schema |

### Results & Analytics (8 tools)

| Tool | Description |
|------|-------------|
| `get_test_summary` | Compact summary: final lift, confidence, significance, verdict |
| `get_test_results` | Detailed results with filter_type (OVERALL, CUSTOMER_COHORT, SITE_PAIR, etc.) |
| `get_lift_explorer_results` | Lift explorer data (JSON equivalent of .avro) |
| `get_lift_explorer_ids` | List valid lift explorer IDs |
| `get_site_pair_lift_manifest` | Per-site-pair lift breakdown |
| `get_prediction_table` | Prediction model results |
| `get_customer_cross` | Customer cross-tabulation data |
| `download_all_test_data` | Comprehensive chart data for a test |

### Rollout Analysis (10 tools)

| Tool | Description |
|------|-------------|
| `list_analyses` | List analyses with optional result status check |
| `get_analysis` | Get analysis configuration by ID |
| `get_analysis_results` | Get results of a completed analysis |
| `get_analysis_with_results` | Config + results in one call |
| `get_recent_analysis_results` | Results for N most recent analyses |
| `create_analysis` | Create a new rollout analysis |
| `update_analysis` | Update analysis configuration |
| `delete_analysis` | Delete an analysis |
| `run_analysis` | Run analysis synchronously (waits for completion) |
| `start_analysis` | Start analysis asynchronously |

### Jobs & Monitoring (4 tools)

| Tool | Description |
|------|-------------|
| `get_jobs_summary` | Running jobs and compute hours for a date range |
| `get_oldest_job_date` | Earliest job date for the client |
| `get_newest_job_date` | Most recent job date for the client |
| `get_clients_jobs_summary` | Job summary across all active clients |

### Discovery (1 tool)

| Tool | Description |
|------|-------------|
| `search_tools` | Search available tools by keyword |

---

## Resources & Prompts

The server also exposes MCP **resources** (read-only context) and **prompts** (workflow templates):

**Resources:**
- `calcs://glossary` — Data format conventions, field meanings (basis points, significance thresholds, etc.)
- `calcs://workflow-guide` — Recommended tool sequences for common analytics tasks

**Prompts:**
- `analyze_test(test_id)` — Step-by-step test analysis workflow
- `compare_recent_tests(count)` — Compare N recent completed tests
- `rollout_review(count)` — Review N recent rollout analyses

---

## Smart Response Management

The server includes built-in response summarization to prevent context window overflow:

- **Test list compaction**: `get_tests` and `get_recent_tests` return only essential fields (id, name, status, dates) instead of raw API responses
- **Summary tools**: `get_test_summary` extracts final lift/confidence/verdict from time-series data
- **Keyword filtering**: Tools like `get_test_results` and `download_all_test_data` accept `filter_keywords` to extract only relevant fields
- **Response size guard**: Middleware warns (to stderr) when responses exceed 100K chars

---

## Project Structure

```
calcs-api-mcp/
├── README.md
├── pyproject.toml
├── .env.example
├── claude-code-config.json
├── cursor-config.json
├── lm-studio-config.json
└── calcs_api/
    ├── __init__.py
    ├── server.py          # FastMCP server setup, lifespan, transport entry points
    ├── client.py          # Async HTTP client (httpx) for all Calcs API endpoints
    ├── auth.py            # Google OAuth provider (optional, HTTP/SSE only)
    ├── middleware.py       # Timing + response size guard middleware
    ├── summarizers.py     # Response compaction and keyword filtering
    ├── resources.py       # MCP resources (glossary, workflow guide)
    ├── prompts.py         # MCP prompt templates
    └── tools/
        ├── __init__.py    # Tool registration coordinator
        ├── tests.py       # Test management tools
        ├── results.py     # Results & analytics tools
        ├── analysis.py    # Rollout analysis tools
        ├── jobs.py        # Job monitoring tools
        └── discovery.py   # Tool search/discovery
```

---

## Troubleshooting

### Server won't start

```bash
# Check Python version (needs 3.13+)
python --version

# Check if ports are in use
lsof -i :8002   # HTTP
lsof -i :8001   # SSE

# Verify UV is installed
uv --version

# Check .env file exists and has CALCS_API_TOKEN
cat .env
```

### "CALCS_API_TOKEN environment variable is required"
Set the token in your `.env` file or export it: `export CALCS_API_TOKEN=your_token`

### "Client header required" / 422 errors
Set `CALCS_DEFAULT_CLIENT` in `.env` or pass `client="name"` to each tool call. Use `get_active_clients` to see valid values.

### Claude Code can't connect
```bash
# Check registered servers
claude mcp list

# Re-add if needed
claude mcp remove calcs-api
claude mcp add calcs-api http://localhost:8002/mcp/
```

### Debug logging
All logs go to stderr. Run the server in a terminal and watch for request timing, API errors, and response size warnings.
