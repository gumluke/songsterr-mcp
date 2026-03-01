#!/bin/bash

set -e
set -o pipefail

# Load environment variables from .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

export PYTHONUNBUFFERED=1

uv run songsterr-mcp
