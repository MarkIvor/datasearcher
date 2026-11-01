# DataSearcher MCP

The DataSearcher MCP server — one of the two usage modes of the unified product.
Full documentation: [root README](../README.md), the **"MCP mode"** section.
(Русская версия: [README.ru.md](../README.ru.md))

## Installation

```bash
pip install -e ".[all]"
```

## Run

```bash
# stdio (Claude Desktop, Cursor, VS Code)
datasearcher-mcp --config /path/to/connections.yaml

# HTTP (remote access)
datasearcher-mcp --transport http --host 0.0.0.0 --port 8000 --auth-token secret123
```

## Configuration

- `connections.yaml` — database connections (example: `connections.example.yaml`)
- Environment variables with the `DATASEARCHER_MCP_` prefix — see `env.example`

Ready-to-use configs can be generated in the web interface:
the **Setup wizard → "MCP" type** creates `connections.yaml` and JSON for
Claude Desktop / Cursor from the connections configured via the UI.
