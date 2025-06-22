# MCP Server Specification

## Overview

The MCP server provides Model Context Protocol integration for Knowledge Engine V2. It serves as the primary interface for LLMs to interact with the knowledge graph.

## Usage

```bash
uv run mcp_server.py --workspace path/to/ws
```

## Command Line Arguments

* `--workspace`: Path to the workspace directory (required)

## Workspace Management

The server maintains a list of available workspaces that it can fetch from:

* **Primary Workspace**: The workspace specified via `--workspace` argument
* **Referenced Workspaces**: Additional workspaces that can be accessed
* **Remote Workspaces**: External workspaces accessible over network
* **Workspace Registry**: Internal list of all accessible workspaces

## Core Classes

* `MCPServer`: Main server class managing workspace and active context
* `ActiveContext`: Manages the current working set of concepts and resources

## MCP Tools

### Core Tools

* `context()`: Serves the current Active Context to the LLM
* `traverse(concept_uri)`: Adds a concept to ActiveContext and returns information

### Concept Management

* `add_concept(path, contents, relations)`: Creates new concepts with automatic link resolution
* `update_concept(concept_uri, contents)`: Modifies existing concept contents
* `move_concept(old_uri, new_path)`: Moves/renames concepts
* `delete_concept(concept_uri)`: Removes concepts from the graph

### Resource Management

* `delete_resource(resource_uri)`: Removes resources from the graph

### Relationship Management

* `link_nodes(source_uri, target_uri, relation_type)`: Creates directed relations
* `unlink_nodes(source_uri, target_uri, relation_type)`: Removes relations

### Remote Operations

* `export_subgraph(concept_uri)`: Returns a minimal subgraph for external fetching
* `fetch_remote_subgraph(concept_uri)`: Fetches a remote concept and persists it locally
* `submit_subgraph(subgraph)`: (Future) Commits a local graph back to remote

## Link Resolution Behavior

* **Resource links**: If referenced resource doesn't exist, automatically create it
* **Concept links**: If referenced concept doesn't exist, leave reference and return warning

## Implementation

* **File**: `mcp_server.py`
* **Protocol**: FastMCP 2.0
* **Database**: SQLite3 database for knowledge storage and querying
* **Schema**: One workspace per SQLite database
