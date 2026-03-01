"""
Songsterr MCP server for Gumstack.
Exposes tools to search and fetch guitar/bass/drum tabs from Songsterr.
"""
from __future__ import annotations

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
# Current Songsterr API (old /a/wa/ and /a/ra/ endpoints are deprecated/404)
API_BASE = "https://www.songsterr.com/api"
VIEW_BASE = "https://www.songsterr.com"

mcp = FastMCP("Songsterr MCP", host="0.0.0.0", port=PORT)


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


def _slug(text: str) -> str:
    """Build URL slug: lowercase, alphanumeric and hyphens only."""
    s = (text or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s or "tab"


def _view_url(song_id: int, artist: str = "", title: str = "") -> str:
    """Current Songsterr tab page URL (old /a/wa/view?r= is deprecated)."""
    slug = f"{_slug(artist)}-{_slug(title)}".strip("-") or "tab"
    return f"{VIEW_BASE}/a/wsa/{slug}-tab-s{song_id}"


def _song_to_tab(s: dict[str, Any]) -> TabResult:
    """Parse one song from API response (api/songs or api/song)."""
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


@mcp.tool()
def search_tabs(pattern: str) -> SearchTabsResponse:
    """Search for guitar, bass, or drum tabs by keyword (song title, artist, or phrase)."""
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{API_BASE}/songs", params={"pattern": pattern})
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, list):
        data = data.get("songs", data) if isinstance(data, dict) else []
    results = _songs_from_json(data)
    return SearchTabsResponse(results=results, count=len(results))


@mcp.tool()
def best_match(query: str) -> BestMatchResponse | None:
    """Get the single best matching tab for a search query (e.g. 'stairway to heaven led zeppelin')."""
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{API_BASE}/songs", params={"pattern": query})
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, list) or len(data) == 0:
        return None
    first = data[0]
    tab = _song_to_tab(first)
    return BestMatchResponse(id=tab.id, title=tab.title, artist=tab.artist, view_url=tab.view_url)


@mcp.tool()
def search_by_artist(artists: str) -> SearchTabsResponse:
    """Get tabs by one or more artist names (comma-separated)."""
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{API_BASE}/songs", params={"pattern": artists.strip()})
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, list):
        data = data.get("songs", data) if isinstance(data, dict) else []
    results = _songs_from_json(data)
    return SearchTabsResponse(results=results, count=len(results))


@mcp.tool()
def get_tab(tab_id: int) -> GetTabResponse | None:
    """Fetch a tab by Songsterr ID. Returns metadata and a working view_url to open the tab in a browser. Tab notation is not available via API — use view_url to view/play on Songsterr."""
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{API_BASE}/song/{tab_id}")
        r.raise_for_status()
        data = r.json()
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
