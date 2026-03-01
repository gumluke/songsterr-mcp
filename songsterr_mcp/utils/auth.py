"""Authentication utilities for Songsterr MCP."""

import os


def get_credentials() -> dict[str, str]:
    """
    Get developer-provided credentials from environment.

    Songsterr's public API does not require an API key. This is kept for
    compatibility with Gumstack template; add API_KEY here if you use a
    licensed Songsterr API later.
    """
    return {
        "api_key": os.environ.get("API_KEY", ""),
    }
