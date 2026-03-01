"""
Songsterr MCP server for Gumstack.
Exposes tools to search and fetch guitar/bass/drum tabs from Songsterr.

Concurrency: All tools are async and use a shared httpx.AsyncClient with a
semaphore to serialize outbound requests. This prevents the event-loop
blocking and MCP protocol state corruption that caused unknown_tool errors
under concurrent load.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.gumstack import GumstackHost
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", 8000))
API_BASE = "https://www.songsterr.com/api"
VIEW_BASE = "https://www.songsterr.com"

mcp = FastMCP("Songsterr MCP", host="0.0.0.0", port=PORT)

# Serialize outbound API calls so concurrent MCP requests don't block the
# event loop or overwhelm the upstream API.  Max 2 concurrent requests.
_semaphore = asyncio.Semaphore(2)

# Lazy-initialized shared async client (created on first use so it lives on
# the running event loop).
_http_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=15.0)
    return _http_client


@mcp.custom_route("/health_check", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


# --- Response models ---


class TabResult(BaseModel):
    """A single tab from search results."""

    id: int = Field(description="Songsterr tab ID")
    title: str = Field(description="Song title")
    artist: str = Field(description="Artist name")
    view_url: str = Field(description="URL to view the tab on Songsterr")


class SearchTabsResponse(BaseModel):
    """Response for tab search."""

    results: list[TabResult] = Field(description="Matching tabs")
    count: int = Field(description="Number of results")


class BestMatchResponse(BaseModel):
    """Response for best-match query."""

    id: int = Field(description="Songsterr tab ID")
    title: str = Field(description="Song title")
    artist: str = Field(description="Artist name")
    view_url: str = Field(description="URL to view the tab on Songsterr")


class GetTabResponse(BaseModel):
    """Response for fetching a single tab by ID. Open view_url in a browser to see the tab notation."""

    id: int = Field(description="Songsterr tab ID")
    title: str = Field(description="Song title")
    artist: str = Field(description="Artist name")
    view_url: str = Field(
        description="Working URL to open the tab on Songsterr (notation is only available in-browser)"
    )
    tracks: list[str] = Field(
        default_factory=list,
        description="Instrument/track names (e.g. Lead Guitar, Bass, Drums)",
    )


# --- Helpers ---


def _slug(text: str) -> str:
    """Build URL slug: lowercase, alphanumeric and hyphens only."""
    s = (text or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s or "tab"


def _view_url(song_id: int, artist: str = "", title: str = "") -> str:
    slug = f"{_slug(artist)}-{_slug(title)}".strip("-") or "tab"
    return f"{VIEW_BASE}/a/wsa/{slug}-tab-s{song_id}"


def _song_to_tab(s: dict[str, Any]) -> TabResult:
    sid = s.get("songId") or s.get("id") or 0
    title = s.get("title") or ""
    artist = s.get("artist") if isinstance(s.get("artist"), str) else str(s.get("artist", ""))
    return TabResult(
        id=int(sid),
        title=title,
        artist=artist,
        view_url=_view_url(int(sid), artist=artist, title=title),
    )


def _songs_from_json(data: list[dict[str, Any]]) -> list[TabResult]:
    return [_song_to_tab(s) for s in data]


async def _songsterr_get(path: str, params: dict[str, str] | None = None) -> Any:
    """Fetch from Songsterr API with semaphore, retries, and error handling."""
    async with _semaphore:
        client = _get_client()
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                r = await client.get(f"{API_BASE}{path}", params=params)
                r.raise_for_status()
                return r.json()
            except httpx.HTTPStatusError as exc:
                logger.warning("Songsterr API %s returned %s (attempt %d)", path, exc.response.status_code, attempt + 1)
                last_exc = exc
                if exc.response.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.PoolTimeout) as exc:
                logger.warning("Songsterr API %s connection error (attempt %d): %s", path, attempt + 1, exc)
                last_exc = exc
                await asyncio.sleep(1 * (attempt + 1))
                continue
        raise last_exc or RuntimeError("Songsterr API request failed after retries")


# --- Tools ---


@mcp.tool()
async def search_tabs(pattern: str) -> SearchTabsResponse:
    """Search for guitar, bass, or drum tabs by keyword (song title, artist, or phrase)."""
    data = await _songsterr_get("/songs", params={"pattern": pattern})
    if not isinstance(data, list):
        data = data.get("songs", data) if isinstance(data, dict) else []
    results = _songs_from_json(data)
    return SearchTabsResponse(results=results, count=len(results))


@mcp.tool()
async def best_match(query: str) -> BestMatchResponse | None:
    """Get the single best matching tab for a search query (e.g. 'stairway to heaven led zeppelin')."""
    data = await _songsterr_get("/songs", params={"pattern": query})
    if not isinstance(data, list) or len(data) == 0:
        return None
    tab = _song_to_tab(data[0])
    return BestMatchResponse(id=tab.id, title=tab.title, artist=tab.artist, view_url=tab.view_url)


@mcp.tool()
async def search_by_artist(artists: str) -> SearchTabsResponse:
    """Get tabs by one or more artist names (comma-separated)."""
    data = await _songsterr_get("/songs", params={"pattern": artists.strip()})
    if not isinstance(data, list):
        data = data.get("songs", data) if isinstance(data, dict) else []
    results = _songs_from_json(data)
    return SearchTabsResponse(results=results, count=len(results))


@mcp.tool()
async def get_tab(tab_id: int) -> GetTabResponse | None:
    """Fetch a tab by Songsterr ID. Returns metadata and a working view_url to open the tab in a browser. Tab notation is not available via API — use view_url to view/play on Songsterr."""
    data = await _songsterr_get(f"/song/{tab_id}")
    if not isinstance(data, dict):
        return None
    tab = _song_to_tab(data)
    tracks = [t.get("name", "").strip() for t in data.get("tracks", []) if t.get("name")]
    return GetTabResponse(
        id=tab.id,
        title=tab.title,
        artist=tab.artist,
        view_url=tab.view_url,
        tracks=tracks,
    )


def main() -> None:
    load_dotenv()
    if os.environ.get("ENVIRONMENT") != "local":
        host = GumstackHost(mcp)
        host.run(host="0.0.0.0", port=PORT)
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
