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
| `get_tab` | Fetch a tab by ID (metadata, track list, and a working view URL) |

## Tab notation

Songsterr’s **public API** only exposes search and song **metadata** (title, artist, track names). The actual **tab notation** (the notes/tablature) is not available via any documented public endpoint — it’s rendered in the browser on Songsterr. Every result includes a **view_url** that uses the current site URL pattern (e.g. `/a/wsa/artist-title-tab-s123`). Open that link to view and play the tab on Songsterr.

## Deploy to Gumstack

1. Connect this repo (**gumluke/songsterr-mcp**) in Gumstack Internal MCPs.
2. Ensure the GitHub App is installed for the repo so pushes trigger deployments.
3. Push to `main`; Gumstack builds and deploys. The server URL is on the server’s Overview tab.

## About

MCP server: Songsterr MCP — search and fetch tabs from Songsterr.
