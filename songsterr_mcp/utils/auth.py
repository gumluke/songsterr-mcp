"""Authentication utilities for Songsterr MCP."""

import os


def get_credentials() -> dict[str, str]:
    """
    Get developer-provided credentials from environment.

    Developer sets this in env vars, user doesn't need to provide anything.
    """
    return {
        "api_key": os.environ.get("API_KEY", ""),
    }
