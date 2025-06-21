# Project Structure

## Implementation Roadmap

### Goal 1: Hello World MCP Server
```
knowledge_engine/
├── __init__.py
├── mcp_server.py          # FastMCP server with hello_world tool
├── main.py               # Entry point (existing)
└── pyproject.toml        # Dependencies (updated)
```

### Goal 2: MVP Implementation
```
knowledge_engine/
├── __init__.py
├── mcp_server.py          # Full MCP server with all tools
├── cli.py                # CLI tool for direct knowledge graph access
├── core/
│   ├── __init__.py
│   ├── knowledge_graph.py # SQLite database and graph operations
│   ├── active_context.py  # ActiveContext management
│   └── models.py         # Data models (Node, Relation, etc.)
├── tools/
│   ├── __init__.py
│   ├── context.py        # context() MCP tool
│   ├── traverse.py       # traverse() MCP tool
│   ├── concepts.py       # add_concept, edit_concept, etc.
│   ├── resources.py      # Resource management tools
│   └── relations.py      # link_nodes, unlink_nodes tools
├── visualization/
│   ├── __init__.py
│   ├── server.py         # HTTP/WebSocket server for viz
│   ├── static/           # React app build
│   └── api/              # REST API endpoints
├── main.py
└── pyproject.toml
```

### Goal 2.5: Dynamic Weights
```
knowledge_engine/
├── ... (previous structure)
├── core/
│   ├── ... (previous)
│   └── weights.py        # Weight management and optimization
├── tools/
│   ├── ... (previous)
│   └── weights.py        # set_relation_weight, get_relation_weights
└── visualization/
    ├── ... (previous)
    └── api/
        └── weights.py    # Weight visualization endpoints
```

### Goals 3-4: External/Remote Graphs
```
knowledge_engine/
├── ... (previous structure)
├── core/
│   ├── ... (previous)
│   ├── workspace.py      # Workspace management
│   └── remote.py         # Remote graph fetching
├── tools/
│   ├── ... (previous)
│   └── remote.py         # Remote workspace tools
└── visualization/
    ├── ... (previous)
    └── api/
        └── remote.py     # Remote graph visualization
```

## Key Implementation Notes

### FastMCP Integration
- Use `fastmcp` library for MCP server implementation
- Install with: `uv run fastmcp install server.py`
- Server entry point: `knowledge_engine.mcp_server:main`

### CLI Tool (Goal 2)
- Direct knowledge graph access (no ActiveContext)
- Query concepts, resources, and relations
- Useful for debugging and manual exploration

### Visualization (Goal 2)
- React + TypeScript + D3.js frontend
- Served by MCP server process
- HTTP API + WebSocket for real-time updates

### Database Schema
- SQLite database per workspace
- Tables: `nodes`, `relations`
- Path-based keys (relative to workspace)

### Development Workflow
- Use `uv run` for all script execution
- Development dependencies: pytest, black, ruff
- Type hints throughout for better developer experience 