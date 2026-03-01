# Dockerfile for Songsterr MCP
# For Gumstack deployment (Knative)
# syntax=docker/dockerfile:1

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files (uv.lock optional; run uv lock locally and commit for reproducible builds)
COPY pyproject.toml README.md ./

# Install uv package manager
RUN pip install --no-cache-dir uv

# Install Python dependencies
# Mount the GAR token as a secret (Gumstack provides this in CI)
RUN --mount=type=secret,id=gar_token \
    set -e && \
    export UV_INDEX_GUMSTACK_PRIVATE_USERNAME=oauth2accesstoken && \
    export UV_INDEX_GUMSTACK_PRIVATE_PASSWORD="$(cat /run/secrets/gar_token)" && \
    uv sync

# Copy application code
COPY . .

# Expose port 8080 (required by Knative)
EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV ENVIRONMENT=production

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health_check || exit 1

CMD ["uv", "run", "songsterr-mcp"]
