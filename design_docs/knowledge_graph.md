# Knowledge Graph Specification

This project defines a knowledge engine designed for LLMs to interact with, with the goal of accelerating agentic understanding of large project structures. While it is currently focused on representing codebases and software knowledge, the underlying system is general and extensible to any domain — from science and design to team procedures and research insights. It forms a persistent, structured, and queryable long-term memory that LLMs can incrementally build, update, and traverse. The graph can represent not only technical knowledge about code, but also general knowledge, such as project plans, meeting summaries, design decisions, and research threads. This enables the LLM to connect high-level concepts with artifacts, conversations, and processes that emerge during real-world collaboration. that LLMs can incrementally build, update, and traverse. The system is optimized for autonomy, multi-agent collaboration, and scalable composition across local and remote workspaces.

## Overview

The knowledge graph is a preprocessed, efficient representation of a codebase that stores and connects information. It serves as an LLM-owned scratch space where language models can dump and retrieve ideas about their work. The graph consists of nodes connected by directed edges (relations), designed to provide rapid access to structured knowledge about software projects.

## LLM Ownership & Control

* **LLM-Managed Content**: The LLM decides what concepts to create and how much detail to include
* **Flexible Granularity**: LLM can choose between high-level concepts or detailed technical descriptions
* **Dynamic Connections**: LLM determines which relationships are important and should be linked
* **Iterative Refinement**: LLM can continuously update and expand concepts as understanding evolves
* **Personal Scratch Space**: Functions as the LLM's working memory for complex development tasks

## Purpose & Benefits

* **Preprocessed Representation**: Transforms raw codebase into structured, queryable knowledge
* **Efficient Access**: Optimized for fast retrieval of relevant information during development
* **Contextual Understanding**: Captures relationships and dependencies that aren't obvious from code alone
* **LLM-Optimized**: Formatted specifically for consumption by language models
* **Incremental Updates**: Can be updated as codebase evolves without full reprocessing
* **Persistent Memory**: Allows LLMs to maintain context across multiple sessions
* **Flexible Schema**: No rigid structure - LLM adapts content organization to its needs

## Node Types

### Resources

* **Purpose**: Contain references to MCP resources that the LLM has access to
* **Examples**:

  * `file://path/to/code.py` - Local files
  * `https://docs.google.com/document/...` - Google Docs
  * `https://example.com/api/docs` - URLs
* **Function**: Act as pointers to actual content/data in the codebase
* **LLM Control**: LLM decides which resources are worth tracking and referencing

### Concepts

* **Purpose**: Represent abstract ideas, patterns, and knowledge extracted from the codebase
* **Examples**:

  * Information about specific classes, functions, or modules
  * Coding standards and architectural patterns used in the repository
  * Team members and their areas of expertise
  * Business logic and domain concepts
  * Design decisions and their rationale
  * LLM's own insights and observations about the code
* **Function**: Capture distilled knowledge and understanding about the codebase
* **LLM Control**: LLM determines content depth, from brief notes to comprehensive documentation

## Relations

* **Structure**: Directed edges between nodes
* **Direction**: From source node to target node
* **Purpose**: Express how concepts and resources relate to each other in the codebase context
* **Weight**: Each relation has a traversal cost (0 to 1, nominally 1)

### Examples

* Concept → Resource: "documented\_by", "implemented\_in", "tested\_by"
* Concept → Concept: "depends\_on", "is\_a", "related\_to", "replaces"
* Resource → Resource: "imports", "references", "extends"

### LLM Control

* LLM decides which relationships are significant enough to model explicitly

## Relation Weights & Traversal

Traversal may cross workspace boundaries if the external workspace is defined in the registry. When a concept from an external graph is encountered and its workspace is known, the engine will fetch its subgraph and continue traversal as long as context and cost limits are respected.

Weights on relations are dynamic and may evolve over time. We are undecided whether these should be driven by LLM requests (e.g., explicit weight-setting) or inferred from access patterns and usage. This decision will be addressed during weight optimization implementation.

The `traverse` API may eventually support a custom cost threshold (`max_cost`) or depth parameter. However, care must be taken to prevent explosive growth in context size — particularly in dense graphs. Safety mechanisms (such as node count caps or hop limits) may be added in the future.

* **Weight Range**: 0 to 1, where 0 means "always load together" and 1 means "standard cost"
* **Traversal Algorithm**: `traverse` uses BFS (Breadth-First Search) with maximum cost of 1
* **Cost Accumulation**: Weights are summed along paths during traversal
* **Auto-Loading**: Relations with weight 0 ensure concepts are always loaded together
* **Context Boundaries**: Traversal stops when cumulative cost would exceed 1

### Examples

* Weight 0: Tightly coupled concepts that should always appear together
* Weight 0.5: Related concepts that may be included if budget allows
* Weight 1: Standard relations that require explicit traversal

## Active Context Building

When `traverse` is called on a concept:

1. Start BFS from the target concept (cost 0)
2. Traverse relations, accumulating weights
3. Include nodes where total path cost ≤ 1
4. Stop traversal on paths that would exceed cost limit
5. Add all discovered nodes to Active Context

## Workspace Storage Layout

Each MCP server instance uses a single SQLite database:

```
~/.knowledge_engine/
  ├── knowledge_<workspace_id>.db    # Single database per MCP server instance
```

The database can contain nodes from multiple workspaces, distinguished by URI namespace:
* `concept://ws1/project` - Concept from workspace 1
* `concept://ws2/project` - Concept from workspace 2
* `file://ws1/src/main.py` - File from workspace 1

## Database Schema

### Design Principles

* **One Database Per MCP Server**: Each MCP server instance maintains its own SQLite database
* **Full URI Storage**: Store complete URIs as primary keys (e.g., `concept://ws/project`)
* **Common Database Location**: Store databases in `~/.knowledge_engine/` for centralized management
* **Cross-Workspace Support**: Single database can contain nodes from multiple workspaces via URI namespace

### Tables

#### nodes

```sql
CREATE TABLE nodes (
    uri TEXT PRIMARY KEY,           -- Full URI: concept://ws/path or file://ws/path
    node_type TEXT NOT NULL,        -- "concept" or "resource"
    name TEXT,                      -- for concepts, null for resources
    content TEXT,                   -- for concepts, null for resources
    metadata JSON,                  -- flexible LLM-defined properties + standard fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### relations

```sql
CREATE TABLE relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_uri TEXT NOT NULL,
    target_uri TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,        -- traversal cost (0 to 1)
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_uri) REFERENCES nodes(uri) ON DELETE CASCADE,
    FOREIGN KEY (target_uri) REFERENCES nodes(uri) ON DELETE CASCADE,
    UNIQUE(source_uri, target_uri, relation_type)  -- prevent duplicates
);
```

### Metadata Standards

#### File Resources (set by bootstrap tool)
* `file_type`: Language/type (python, javascript, markdown, etc.)
* `extension`: File extension (.py, .js, .md, etc.)
* `size_bytes`: File size in bytes
* `line_count`: Number of lines (for text files)
* `mime_type`: MIME type
* `last_modified`: Last modification timestamp

#### Directory Concepts (set by bootstrap tool)
* `node_type`: "directory"
* `file_count`: Number of files in directory
* `total_size`: Total size of all files
* `depth`: Directory depth from workspace root

#### LLM-Defined Properties
* Any additional properties the LLM wants to track
* Examples: `importance`, `complexity`, `review_status`, `team_owner`

## Active Context Management

### LRU-Based Context Limits
* **Configurable Size**: Maximum number of nodes in ActiveContext (default: 100)
* **LRU Eviction**: Least recently used nodes are removed when limit is exceeded
* **Ephemeral Storage**: ActiveContext resets on MCP server restart
* **LLM Prompting**: Server prompts LLM to add local concepts about previous work

### Context Building
When `traverse` is called on a concept:

1. Start BFS from the target concept (cost 0)
2. Traverse relations, accumulating weights
3. Include nodes where total path cost ≤ 1
4. Stop traversal on paths that would exceed cost limit
5. Add all discovered nodes to Active Context (respecting LRU limits)

## Link Resolution Behavior

* **Resource links**: If referenced resource doesn't exist, automatically create it
* **Concept links**: If referenced concept doesn't exist, leave reference and return warning to LLM
* **Visualization**: Show missing concept links in red to indicate broken references
* **LLM Notifications**: Return prompts notifying the LLM that things are missing

## MCP Server Tools Interface

### Merge Conflicts

Conflicting edits across local and remote workspaces are resolved via MCP sampling — the LLM is shown multiple versions of a concept and decides how to reconcile them during editing or traversal.

### Dead Links

If a concept fetched from a remote workspace no longer exists, the server returns an error. This is surfaced to the LLM as a broken link — enabling intelligent fallback, redirection, or warning generation (similar to how human developers handle dead docs).

### Local and Remote Subgraph Submission

To support write operations, we propose a unified commit mechanism for both local and remote changes.

* **Local Commits**: Local edits to the knowledge graph should also be committed. Each commit represents a meaningful change to a concept or set of relations and can be stored as a Git commit within the local workspace directory. This enables:

  * Easy rollback
  * Change tracking over time
  * Compatibility with remote sync workflows

* **Authentication & Scoping**: Each workspace registry entry could include an auth token and scope (e.g., write access to `/infra/*`). These tokens would be required to call `submit_subgraph()`.

* **Fine-Grained Commits**: Rather than submitting an entire local graph, clients may submit a set of changes (added, modified, removed nodes/relations). This enables precise remote updates and conflict mitigation.

* **History via Git**: Each workspace may be backed by a Git repository. Commits (both local and remote) would capture:

  * Concept path(s) modified
  * Diffed content
  * Author metadata (from token scope or local config)
  * Commit message (optional from LLM)

  Remote servers can validate, record, and merge these updates using Git itself as the history and merge backend.

These ideas aim to preserve trust, traceability, and reviewability in multi-agent knowledge editing workflows. To support remote write operations, we propose a few ideas:

* **Authentication & Scoping**: Each workspace registry entry could include an auth token and scope (e.g., write access to `/infra/*`). These tokens would be required to call `submit_subgraph()`.

* **Fine-Grained Commits**: Rather than submitting an entire local graph, clients may submit a set of changes (added, modified, removed nodes/relations). This enables precise remote updates and conflict mitigation.

* **History via Git**: Each workspace may be backed by a Git repository. Commits to remote workspaces would create a Git commit with:

  * Concept path(s) modified
  * Diffed content
  * Author metadata (from token scope)
  * Commit message (optional from LLM)

  Remote servers can validate, record, and merge these updates using Git itself as the history and merge backend.

These ideas aim to preserve trust, traceability, and reviewability in multi-agent knowledge editing workflows.

### Merge Conflicts

Conflicting edits across local and remote workspaces are resolved via MCP sampling — the LLM is shown multiple versions of a concept and decides how to reconcile them during editing or traversal.

### Dead Links

If a concept fetched from a remote workspace no longer exists, the server returns an error. This is surfaced to the LLM as a broken link — enabling intelligent fallback, redirection, or warning generation (similar to how human developers handle dead docs).

---

## ActiveContext vs. Knowledge DB

| Layer             | What it contains                | Volatility             | Scope              |
| ----------------- | ------------------------------- | ---------------------- | ------------------ |
| **ActiveContext** | In-memory graph of current work | Ephemeral              | LLM working memory |
| **Knowledge DB**  | SQLite-backed concept store     | Persistent             | Workspace-specific |
| **Remote Server** | Canonical knowledge repository  | Shared source-of-truth | Organization-wide  |
