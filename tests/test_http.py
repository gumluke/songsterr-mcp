#!/usr/bin/env python3
"""Test the MCP server using streamable HTTP transport."""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Package name for imports
PACKAGE_NAME = "songsterr_mcp"
SERVER_URL = "http://localhost:8000/mcp"


def get_project_root() -> Path:
    """Find project root by looking for pyproject.toml."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (no pyproject.toml found)")


def load_env():
    """Load .env from project root, raise if not found."""
    root = get_project_root()
    env_file = root / ".env"
    if not env_file.exists():
        raise FileNotFoundError(
            f".env file not found at {env_file}\n"
            "Copy .env.example to .env and fill in your credentials."
        )
    load_dotenv(env_file)
    return root


class ServerProcess:
    """Context manager to run the server as a subprocess."""

    def __init__(self, root: Path, host: str = "0.0.0.0", port: int = 8000):
        self.root = root
        self.host = host
        self.port = port
        self.process = None

    def __enter__(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.root)
        env["ENVIRONMENT"] = "local"

        # Start server with streamable HTTP transport
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                PACKAGE_NAME + ".server",
                "--transport",
                "streamable-http",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to start
        print(f"⏳ Waiting for server to start on port {self.port}...")
        time.sleep(2)

        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f"Server failed to start:\n{stderr.decode()}")

        print(f"✅ Server running on http://{self.host}:{self.port}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("🛑 Server stopped")


async def test_http():
    """Connect to the server via HTTP and test its tools."""
    print("🔌 Connecting to server via streamable HTTP...")

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected and initialized\n")

            # List available tools
            tools_response = await session.list_tools()
            print("🔧 Available tools:")
            for tool in tools_response.tools:
                print(f"   - {tool.name}: {tool.description}")
            print()

            # Test the example_tool
            print("🧪 Testing example_tool...")
            result = await session.call_tool("example_tool", {"query": "hello world"})
            print(f"   Result: {result.content}")
            print()

            print("✅ All tests passed!")


def main():
    root = load_env()
    with ServerProcess(root, port=8000):
        asyncio.run(test_http())


if __name__ == "__main__":
    main()
