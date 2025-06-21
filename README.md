# Knowledge Engine

A self-documenting knowledge graph system that provides MCP (Model Context Protocol) tools for Claude Desktop integration.

## Goal 0: Hello World MCP Server ✅

This implementation provides a basic MCP server that connects with Claude Desktop and includes a simple `hello_world` tool.

### Features

- ✅ Minimal MCP server using FastMCP
- ✅ `hello_world` tool that returns "Hello World!"
- ✅ MCP configuration for Claude Desktop integration
- ✅ Simplified project structure focused on MCP server

### Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Start the MCP server:**
   ```bash
   uv run mcp-server
   ```

### Global Installation (Recommended for IDE/Editor Integration)

For a more seamless integration with editors like Claude Desktop or Cursor/VSCode, it's recommended to install the `knowledge-engine` package globally within `uv`'s environment.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/knowledge_engine.git
    cd knowledge_engine
    ```

2.  **Install the package globally:**
    This command makes the `mcp-server` command available system-wide for `uv`.
    ```bash
    uv pip install --system .
    ```

### Editor Integration

Once the package is installed, you can configure your editor to use the `knowledge-engine` MCP server.

**Claude Desktop**

Add the following to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "knowledge-engine": {
      "command": "uv",
      "args": [
        "run",
        "mcp-server"
      ]
    }
  }
}
```

**Cursor / VSCode**

Add the following to your `settings.json`:
```json
{
  "mcp.servers": {
    "knowledge-engine": {
        "command": "uv",
        "args": ["run", "mcp-server"]
    }
  }
}
```

### Success Criteria

- ✅ Claude Desktop can connect to and invoke tools from the knowledge engine server
- ✅ The `hello_world` tool can be invoked from the LLM interface and returns "Hello World!"

## Next Steps

This completes Goal 0. The next goal is **Goal 1: MVP Implementation - Self-Documenting Knowledge Graph** which will add:

- Self-documentation capabilities
- Knowledge graph storage with SQLite
- Core MCP tools (`context`, `traverse`, `add_concept`, etc.)
- Web-based visualization interface
- Active Context management with BFS traversal
- CLI tools for knowledge graph management

