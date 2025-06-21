# Bootstrapping Tool

The bootstrapping tool automatically imports all project files as resource nodes and creates the initial knowledge graph structure.

## Purpose

* **Initial Setup**: Create the foundational knowledge graph for a new workspace
* **Resource Discovery**: Automatically detect and import all files in the workspace
* **Metadata Extraction**: Extract file types, sizes, and other relevant metadata
* **Directory Structure**: Create concept nodes representing the project structure
* **Self-Documentation**: Establish the knowledge graph as the primary documentation source

## Usage

```bash
uv run cli.py bootstrap --workspace path/to/ws
```

## Implementation

### File Discovery
* **Recursive Scan**: Walk through all files and directories in the workspace
* **Filtering**: Exclude common patterns (`.git/`, `node_modules/`, `__pycache__/`, etc.)
* **File Types**: Detect file extensions and MIME types for metadata

### Resource Node Creation
For each discovered file, create a resource node:

```sql
INSERT INTO nodes (uri, node_type, metadata) VALUES (
    'file://ws/path/to/file.py',
    'resource',
    '{
        "file_type": "python",
        "extension": ".py",
        "size_bytes": 1234,
        "last_modified": "2024-01-01T00:00:00Z",
        "mime_type": "text/x-python",
        "line_count": 50
    }'
);
```

### Directory Structure Concepts
Create concept nodes for each directory level:

```sql
INSERT INTO nodes (uri, node_type, name, content, metadata) VALUES (
    'concept://ws/src',
    'concept',
    'Source Code Directory',
    'Contains the main source code files for the project.',
    '{
        "node_type": "directory",
        "file_count": 25,
        "total_size": 50000
    }'
);
```

### Automatic Relations
Create relations based on directory structure:

* **Directory Hierarchy**: `concept://ws/src` → `concept://ws/src/components`
* **File Containment**: `concept://ws/src` → `file://ws/src/main.py`
* **File Types**: `concept://ws/python-files` → `file://ws/src/main.py`

### Metadata Standards

#### File Resources
* `file_type`: Language/type (python, javascript, markdown, etc.)
* `extension`: File extension (.py, .js, .md, etc.)
* `size_bytes`: File size in bytes
* `line_count`: Number of lines (for text files)
* `mime_type`: MIME type
* `last_modified`: Last modification timestamp

#### Directory Concepts
* `node_type`: "directory"
* `file_count`: Number of files in directory
* `total_size`: Total size of all files
* `depth`: Directory depth from workspace root

#### Special Files
* `package.json`, `pyproject.toml`, `requirements.txt`: Mark as configuration files
* `README.md`, `docs/`: Mark as documentation
* `.gitignore`, `.env`: Mark as configuration

## Root Concept

Create the workspace root concept:

```sql
INSERT INTO nodes (uri, node_type, name, content, metadata) VALUES (
    'concept://ws/project',
    'concept',
    'Project Root',
    'Root concept for the workspace. Contains all project files and structure.',
    '{
        "node_type": "workspace_root",
        "workspace_path": "/path/to/ws",
        "total_files": 100,
        "total_size": 500000
    }'
);
```

## Post-Bootstrap State

After bootstrapping, the knowledge graph contains:

* **Resource Nodes**: All files in the workspace with metadata
* **Concept Nodes**: Directory structure and project organization
* **Relations**: File containment and directory hierarchy
* **Root Concept**: Entry point for LLM exploration

## LLM Integration

The bootstrapping tool provides a foundation for LLM exploration:

* **Self-Documentation**: LLM can traverse the graph to understand project structure
* **File Discovery**: LLM can find relevant files through concept traversal
* **Metadata Access**: LLM can use file metadata for intelligent decisions
* **Structure Understanding**: Directory concepts help LLM understand project organization

## Future Enhancements

* **Content Analysis**: Extract imports, dependencies, and function signatures
* **Git Integration**: Include git history and authorship information
* **Dependency Mapping**: Create relations between dependent files
* **Configuration Parsing**: Extract project configuration and settings 