# Songsterr MCP

MCP server for [Songsterr](https://www.songsterr.com) guitar, bass, and drum tabs. Deploys to [Gumstack](https://gumstack.com) as an Internal MCP.

**Repo:** [github.com/gumluke/songsterr-mcp](https://github.com/gumluke/songsterr-mcp)

## Setup

```bash
# Install dependencies (requires uv)
uv sync

# If you add or change dependencies, run and commit uv.lock for reproducible builds
# uv lock

# Optional: copy env for local overrides
cp env.example .env
```

## Local development

```bash
# Run the server (streamable-http on PORT)
./run.sh

# Or
uv run songsterr-mcp
```

Set `ENVIRONMENT=local` in `.env` to use streamable-http; otherwise the server uses GumstackHost (for deployed env).

## Authentication

This server uses **No Authentication**. Songsterr’s public API does not require user credentials or an API key. Users don’t provide anything in the Gumstack UI.

## Tools

| Tool | Description |
|------|-------------|
| `search_tabs` | Search for guitar, bass, or drum tabs by keyword (song title, artist, or phrase) |
| `best_match` | Get the single best matching tab for a search query (e.g. "enter sandman") |
| `search_by_artist` | Get tabs by one or more artist names (comma-separated) |
| `get_tab` | Fetch a specific tab by its Songsterr ID (returns tab info and view URL) |

## Deploy to Gumstack

1. Connect this repo (**gumluke/songsterr-mcp**) in Gumstack Internal MCPs.
2. Ensure the GitHub App is installed for the repo so pushes trigger deployments.
3. Push to `main`; Gumstack builds and deploys. The server URL is on the server’s Overview tab.

## About

MCP server: Songsterr MCP — search and fetch tabs from Songsterr.
