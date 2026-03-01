"""
Songsterr MCP server for Gumstack.
Exposes tools to search and fetch guitar/bass/drum tabs from Songsterr.
"""
from __future__ import annotations

import json
import logging
import os
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
BASE = "https://www.songsterr.com"

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
    """Response for fetching a single tab by ID."""

    id: int = Field(description="Songsterr tab ID")
    title: str = Field(description="Song title")
    artist: str = Field(description="Artist name")
    view_url: str = Field(description="URL to view the tab on Songsterr")
    raw_preview: str | None = Field(
        default=None,
        description="Short preview of tab content if available (may be HTML)",
    )


def _songs_from_json(data: list[dict[str, Any]]) -> list[TabResult]:
    out: list[TabResult] = []
    for s in data:
        sid = s.get("id") or s.get("songId") or 0
        title = s.get("title") or ""
        artist = (
            s.get("artist", {}).get("name", "")
            if isinstance(s.get("artist"), dict)
            else str(s.get("artist", ""))
        )
        out.append(
            TabResult(
                id=int(sid),
                title=title,
                artist=artist,
                view_url=f"{BASE}/a/wa/view?r={sid}",
            )
        )
    return out


@mcp.tool()
def search_tabs(pattern: str) -> SearchTabsResponse:
    """Search for guitar, bass, or drum tabs by keyword (song title, artist, or phrase)."""
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{BASE}/a/ra/songs.json", params={"pattern": pattern})
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, list):
        data = data.get("songs", data) if isinstance(data, dict) else []
    results = _songs_from_json(data)
    return SearchTabsResponse(results=results, count=len(results))


@mcp.tool()
def best_match(query: str) -> BestMatchResponse | None:
    """Get the single best matching tab for a search query (e.g. 'enter sandman')."""
    with httpx.Client(timeout=15.0) as client:
        r = client.get(
            f"{BASE}/a/wa/bestMatchForQueryStringPart",
            params={"s": query},
        )
        r.raise_for_status()
        data = r.json()
    if not data:
        return None
    if isinstance(data, dict):
        sid = data.get("id") or data.get("songId") or 0
        title = data.get("title") or ""
        artist = (
            data.get("artist", {}).get("name", "")
            if isinstance(data.get("artist"), dict)
            else str(data.get("artist", ""))
        )
        return BestMatchResponse(
            id=int(sid),
            title=title,
            artist=artist,
            view_url=f"{BASE}/a/wa/view?r={sid}",
        )
    return None


@mcp.tool()
def search_by_artist(artists: str) -> SearchTabsResponse:
    """Get tabs by one or more artist names (comma-separated)."""
    with httpx.Client(timeout=15.0) as client:
        r = client.get(
            f"{BASE}/a/ra/songs/byartists.json",
            params={"artists": artists.strip()},
        )
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, list):
        data = data.get("songs", data) if isinstance(data, dict) else []
    results = _songs_from_json(data)
    return SearchTabsResponse(results=results, count=len(results))


@mcp.tool()
def get_tab(tab_id: int) -> GetTabResponse | None:
    """Fetch a specific tab by its Songsterr ID (returns tab info and view URL)."""
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{BASE}/a/wa/view", params={"r": tab_id})
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        raw_preview: str | None = None
        if "application/json" in content_type:
            data = r.json()
            if isinstance(data, dict):
                sid = data.get("id") or data.get("songId") or tab_id
                title = data.get("title") or ""
                artist = (
                    data.get("artist", {}).get("name", "")
                    if isinstance(data.get("artist"), dict)
                    else str(data.get("artist", ""))
                )
                return GetTabResponse(
                    id=int(sid),
                    title=title,
                    artist=artist,
                    view_url=f"{BASE}/a/wa/view?r={sid}",
                    raw_preview=json.dumps(data)[:2000] if data else None,
                )
        text = r.text
        raw_preview = (text[:3000] + "...") if len(text) > 3000 else (text or None)
    return GetTabResponse(
        id=tab_id,
        title="",
        artist="",
        view_url=f"{BASE}/a/wa/view?r={tab_id}",
        raw_preview=raw_preview,
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
