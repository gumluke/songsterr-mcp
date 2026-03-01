# Gumstack MCP Server

Gumstack MCP servers are optimzied for gumstack platform and integration with gumloop. Following this guide will help you build a server that is optimized for gumstack and gumloop.

`gumstack-mcp` package is available at: `https://us-west1-python.pkg.dev/gumstack-public/gumstack-mcp/simple/`

## Commands

- Install deps: `uv sync`
- Run server: `uv run server`
- Run tests: `uv run pytest`
- Add package: `uv add <package>`
- Lint: `uv run ruff check --fix`

## Project Structure

```
config.yaml          # Server metadata, auth config, tool declarations
src/
├── server.py        # FastMCP server + tool definitions
└── utils/
    └── auth.py      # get_credentials() helper
tests/               # pytest tests
.env                 # Local environment variables
```

## config.yaml

All tools must be declared in `config.yaml` to be detected by gumstack:

```yaml
tools:
  - name: "tool_name"
    description: "What the tool does"
```

Tool name must match the function name in `server.py`. Without this entry, gumstack won't know the tool exists.

## Rules

**Always define output schema**: Every tool must have a return type annotation (BaseModel preferred). Gumloop uses output schemas for downstream node connections.

**Describe everything**: Tool docstrings, parameter descriptions via `Field(description=...)`, and model field descriptions. Better descriptions = better LLM tool selection.

**One tool, one job**: Keep tools focused. Split complex operations into multiple tools for better observability and tool restriction.

**Write tests**: Add a test for each tool. Auth supports local environment.

**Avoid**:
- Bare `dict` returns without type hints (no schema generated)
- Missing docstrings on tools
- Hardcoded credentials (use `get_credentials()`)
- Blocking I/O in async tools (use httpx, not requests)
- Catching broad exceptions without re-raising
- Changing auth type after server creation (not supported)
- Env vars starting with `GUMLOOP_` or `GUMSTACK_` (reserved, will be rejected)

## get_credentials()

Located in `src/utils/auth.py`. Returns `dict[str, str]` with credential keys matching `config.yaml`.

**For cred/oauth types** (async):
- Signature: `async def get_credentials() -> dict[str, str]`
- Must be awaited in async tools
- Returns keys defined in `config.yaml` credentials section
- OAuth type returns `{"access_token": "..."}`
- Cred type returns `{"<credential_name>": "..."}` matching config.yaml

**For none type** (sync):
- Signature: `def get_credentials() -> dict[str, str]`
- Reads directly from env vars
- Returns `{"<credential_name>": os.environ.get("<CREDENTIAL_NAME>")}`

**Local testing**: Set `ENVIRONMENT=local` in `.env`. Function reads from `LOCAL_*` env vars instead of calling backend.

## Tool Output Schema

Return type determines output schema sent to gumloop:
- `BaseModel` → schema from model fields (preferred)
- `TypedDict` → schema from typed keys
- `dict[str, T]` → root-level dict schema
- `list[T]`, `int`, `str`, etc. → wrapped as `{"result": <value>}`
- No annotation → unstructured text only, breaks gumloop connections