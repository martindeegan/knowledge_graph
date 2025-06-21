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

### Claude Desktop Integration

1. Copy the `mcp-config.json` file to your Claude Desktop configuration directory
2. Restart Claude Desktop
3. The `knowledge-engine` server should now be available with the `hello_world` tool

### MCP Configuration

```json
{
  "mcpServers": {
    "knowledge-engine": {
      "command": "uv",
      "args": ["run", "mcp-server"],
      "env": {},
      "cwd": "C:\\Users\\mddee\\knowledge_engine"
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

