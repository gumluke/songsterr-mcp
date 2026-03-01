import logging
import os

from dotenv import load_dotenv
from mcp.gumstack import GumstackHost
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from songsterr_mcp.utils.auth import get_credentials


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get port from environment variable (default 8000 for local, 8080 for Knative)
PORT = int(os.environ.get("PORT", 8000))

mcp = FastMCP("Songsterr MCP", host="0.0.0.0", port=PORT)

# Health check endpoint for Knative readiness/liveness probes
@mcp.custom_route("/health_check", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})

@mcp.tool()
def example_tool(query: str) -> str:
    """
    Example tool using developer-provided API key.

    Args:
        query: The query to process
    """
    creds = get_credentials()
    api_key = creds.get("api_key", "")
    logger.info("Processing with credential: %s...", api_key[:8])
    return f"Processed: {query}"


def main():
    load_dotenv()
    if os.environ.get("ENVIRONMENT") != "local":
        host = GumstackHost(mcp)

        host.run(host="0.0.0.0", port=PORT)
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()