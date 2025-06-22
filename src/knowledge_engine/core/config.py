#!/usr/bin/env python3
"""
Configuration management for the Knowledge Engine.
"""
from pathlib import Path
import toml
import json

def get_knowledge_dir() -> Path:
    """Returns the path to the ~/.knowledge directory."""
    knowledge_dir = Path.home() / ".knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    return knowledge_dir

def get_workspaces_path() -> Path:
    """Returns the path to the workspaces metadata file."""
    return get_knowledge_dir() / "workspaces.json"

def read_workspaces() -> dict:
    """Reads the workspaces metadata file."""
    workspaces_path = get_workspaces_path()
    if not workspaces_path.exists():
        return {}
    with open(workspaces_path, "r") as f:
        return json.load(f)

def write_workspaces(workspaces: dict):
    """Writes to the workspaces metadata file."""
    workspaces_path = get_workspaces_path()
    with open(workspaces_path, "w") as f:
        json.dump(workspaces, f, indent=4)

def register_workspace(workspace_id: str, root_path: Path):
    """Adds or updates a workspace's metadata."""
    workspaces = read_workspaces()
    workspaces[workspace_id] = {"root_path": str(root_path.resolve())}
    write_workspaces(workspaces)

def find_workspace_root(start_path: Path | None = None) -> Path | None:
    """
    Finds the workspace root by searching for 'ke_config.toml' upwards.
    """
    current_path = start_path or Path.cwd()
    while current_path != current_path.parent:
        config_file = current_path / "ke_config.toml"
        if config_file.exists():
            return current_path
        current_path = current_path.parent
    return None

def get_db_path_from_workspace_id(workspace_id: str) -> Path:
    """
    Constructs the database path from a workspace ID.
    """
    db_dir = get_knowledge_dir()
    return db_dir / f"{workspace_id}.db"

def get_db_path() -> Path:
    """
    Determines the database path based on ke_config.toml or defaults.
    """
    root_path = find_workspace_root()
    if root_path:
        config_path = root_path / "ke_config.toml"
        with open(config_path, "r") as f:
            config = toml.load(f)
            workspace_id = config.get("project", {}).get("workspace_id")
            if workspace_id:
                return get_db_path_from_workspace_id(workspace_id)
    # This default is now less likely to be used, but kept as a fallback.
    return Path("knowledge.db")

def get_context_path() -> Path:
    """
    Determines the active context path based on ke_config.toml or defaults.
    """
    root_path = find_workspace_root()
    if root_path:
        config_path = root_path / "ke_config.toml"
        with open(config_path, "r") as f:
            config = toml.load(f)
            workspace_id = config.get("project", {}).get("workspace_id")
            if workspace_id:
                context_dir = get_knowledge_dir()
                return context_dir / f"{workspace_id}.context.json"
    # Default to a local file if not in a workspace
    return Path(".active_context.json") 