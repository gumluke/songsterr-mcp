# Dockerfile for Songsterr MCP
# Auto-generated from gumstack-mcp-template-python
# syntax=docker/dockerfile:1

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install uv package manager
RUN pip install --no-cache-dir uv

# Install Python dependencies
# Mount the GAR token as a secret
RUN --mount=type=secret,id=gar_token \
    set -e && \
    export UV_INDEX_GUMSTACK_PRIVATE_USERNAME=oauth2accesstoken && \
    export UV_INDEX_GUMSTACK_PRIVATE_PASSWORD="$(cat /run/secrets/gar_token)" && \
    uv sync

# Copy application code
COPY . .

# Expose port 8080 (required by Knative)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV ENVIRONMENT=production

# Health check endpoint
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health_check || exit 1

# Run the MCP server
CMD ["uv", "run", "songsterr-mcp"]