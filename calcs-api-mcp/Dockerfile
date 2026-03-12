FROM python:3.13-slim AS base

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (cacheable layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY calcs_api/ calcs_api/

# Cloud Run injects PORT env var; default to 8080
ENV PORT=8080
EXPOSE 8080

# Run HTTP transport (reads PORT env var)
CMD ["uv", "run", "calcs-api-http"]
