#!/usr/bin/env python3
"""
Workspace management for the Knowledge Engine.

This module provides a centralized way to handle workspace operations,
ensuring consistent path resolution regardless of the current working directory.
"""
import json
import toml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class WorkspaceConfig:
    """Configuration data for a workspace."""
    workspace_id: str
    root_path: Path
    config_data: Dict[str, Any]
    
    @property
    def config_path(self) -> Path:
        """Path to the ke_config.toml file."""
        return self.root_path / "ke_config.toml"
    
    @property
    def db_path(self) -> Path:
        """Path to the workspace database."""
        knowledge_dir = get_knowledge_dir()
        return knowledge_dir / f"{self.workspace_id}.db"
    
    @property
    def context_path(self) -> Path:
        """Path to the workspace active context file."""
        knowledge_dir = get_knowledge_dir()
        return knowledge_dir / f"{self.workspace_id}.context.json"
    
    def get_relative_path(self, path: str | Path) -> Path:
        """Convert a path relative to the workspace root."""
        return self.root_path / path
    
    def get_absolute_path(self, path: str | Path) -> Path:
        """Get absolute path, resolving relative paths against workspace root."""
        path = Path(path)
        if path.is_absolute():
            return path
        return (self.root_path / path).resolve()


class Workspace:
    """
    Centralized workspace management.
    
    This class provides a single point of access for all workspace operations,
    ensuring consistent behavior regardless of current working directory.
    """
    
    def __init__(self, config: WorkspaceConfig):
        self._config = config
    
    @property
    def config(self) -> WorkspaceConfig:
        """Get the workspace configuration."""
        return self._config
    
    @property
    def id(self) -> str:
        """Get the workspace ID."""
        return self._config.workspace_id
    
    @property
    def root(self) -> Path:
        """Get the workspace root path."""
        return self._config.root_path
    
    @property
    def db_path(self) -> Path:
        """Get the database path for this workspace."""
        return self._config.db_path
    
    @property
    def context_path(self) -> Path:
        """Get the active context path for this workspace."""
        return self._config.context_path
    
    def get_path(self, relative_path: str | Path) -> Path:
        """Get a path relative to the workspace root."""
        return self._config.get_relative_path(relative_path)
    
    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path, treating relative paths as relative to workspace root."""
        return self._config.get_absolute_path(path)
    
    def reload_config(self) -> None:
        """Reload the workspace configuration from disk."""
        if self._config.config_path.exists():
            with open(self._config.config_path, 'r') as f:
                self._config.config_data = toml.load(f)
    
    def save_config(self) -> None:
        """Save the current configuration to disk."""
        with open(self._config.config_path, 'w') as f:
            toml.dump(self._config.config_data, f)
    
    def get_config_value(self, key_path: str, default=None):
        """
        Get a configuration value using dot notation.
        
        Example: get_config_value("project.workspace_id")
        """
        keys = key_path.split('.')
        value = self._config.config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set_config_value(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Example: set_config_value("project.workspace_id", "my_workspace")
        """
        keys = key_path.split('.')
        config = self._config.config_data
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value


def get_knowledge_dir() -> Path:
    """Returns the path to the ~/.knowledge directory."""
    knowledge_dir = Path.home() / ".knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    return knowledge_dir


def get_workspaces_metadata_path() -> Path:
    """Returns the path to the workspaces metadata file."""
    return get_knowledge_dir() / "workspaces.json"


def read_workspaces_metadata() -> Dict[str, Dict[str, str]]:
    """Reads the workspaces metadata file."""
    metadata_path = get_workspaces_metadata_path()
    if not metadata_path.exists():
        return {}
    with open(metadata_path, "r") as f:
        return json.load(f)


def write_workspaces_metadata(workspaces: Dict[str, Dict[str, str]]) -> None:
    """Writes to the workspaces metadata file."""
    metadata_path = get_workspaces_metadata_path()
    with open(metadata_path, "w") as f:
        json.dump(workspaces, f, indent=4)


def register_workspace(workspace_id: str, root_path: Path) -> None:
    """Register a workspace in the global metadata."""
    workspaces = read_workspaces_metadata()
    workspaces[workspace_id] = {"root_path": str(root_path.resolve())}
    write_workspaces_metadata(workspaces)


def find_workspace_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the workspace root by searching for 'ke_config.toml' upwards from start_path.
    
    Args:
        start_path: Directory to start searching from. Defaults to current directory.
        
    Returns:
        Path to workspace root, or None if not found.
    """
    current_path = start_path or Path.cwd()
    current_path = current_path.resolve()
    
    while current_path != current_path.parent:
        config_file = current_path / "ke_config.toml"
        if config_file.exists():
            return current_path
        current_path = current_path.parent
    return None


def find_workspace_by_name(workspace_name: str, search_paths: Optional[list[Path]] = None) -> Optional[Path]:
    """
    Find a workspace directory by name.
    
    Args:
        workspace_name: Name of the workspace directory to find
        search_paths: Additional paths to search. Defaults to common locations.
        
    Returns:
        Path to workspace root, or None if not found.
    """
    if search_paths is None:
        search_paths = [
            Path.cwd(),
            Path.home(),
        ]
    
    # First try traversing upwards from current directory
    current_path = Path.cwd()
    while current_path != current_path.parent:
        potential_workspace = current_path / workspace_name
        if potential_workspace.exists() and (potential_workspace / "ke_config.toml").exists():
            return potential_workspace
        current_path = current_path.parent
    
    # Then try common locations
    for search_path in search_paths:
        potential_workspace = search_path / workspace_name
        if potential_workspace.exists() and (potential_workspace / "ke_config.toml").exists():
            return potential_workspace
    
    return None


def load_workspace_config(workspace_root: Path) -> WorkspaceConfig:
    """
    Load workspace configuration from a workspace root directory.
    
    Args:
        workspace_root: Path to the workspace root directory
        
    Returns:
        WorkspaceConfig object
        
    Raises:
        ValueError: If workspace_root doesn't contain a valid ke_config.toml
    """
    config_path = workspace_root / "ke_config.toml"
    if not config_path.exists():
        raise ValueError(f"No ke_config.toml found in {workspace_root}")
    
    with open(config_path, 'r') as f:
        config_data = toml.load(f)
    
    # Extract workspace_id from config
    workspace_id = config_data.get("project", {}).get("workspace_id")
    if not workspace_id:
        # Fall back to directory name if no workspace_id in config
        workspace_id = workspace_root.name
    
    return WorkspaceConfig(
        workspace_id=workspace_id,
        root_path=workspace_root,
        config_data=config_data
    )


def load_workspace_from_name(workspace_name: str, search_paths: Optional[list[Path]] = None) -> Optional[Workspace]:
    """
    Load a workspace by name, searching in common locations.
    
    Args:
        workspace_name: Name of the workspace to load
        search_paths: Additional paths to search
        
    Returns:
        Workspace object, or None if not found
    """
    workspace_root = find_workspace_by_name(workspace_name, search_paths)
    if not workspace_root:
        return None
    
    config = load_workspace_config(workspace_root)
    return Workspace(config)


def load_workspace_from_current_dir() -> Optional[Workspace]:
    """
    Load workspace from current directory by searching upwards for ke_config.toml.
    
    Returns:
        Workspace object, or None if not in a workspace
    """
    workspace_root = find_workspace_root()
    if not workspace_root:
        return None
    
    config = load_workspace_config(workspace_root)
    return Workspace(config)


def load_workspace(workspace_name: Optional[str] = None, search_paths: Optional[list[Path]] = None) -> Optional[Workspace]:
    """
    Load a workspace using flexible resolution logic.
    
    Args:
        workspace_name: Optional workspace name. If None, searches from current directory.
        search_paths: Additional paths to search when looking for named workspace.
        
    Returns:
        Workspace object, or None if not found
    """
    if workspace_name:
        return load_workspace_from_name(workspace_name, search_paths)
    else:
        return load_workspace_from_current_dir()


def create_workspace(workspace_root: Path, workspace_id: Optional[str] = None, 
                    config_data: Optional[Dict[str, Any]] = None) -> Workspace:
    """
    Create a new workspace with ke_config.toml.
    
    Args:
        workspace_root: Directory to create workspace in
        workspace_id: Workspace identifier. Defaults to directory name.
        config_data: Additional configuration data
        
    Returns:
        Workspace object
    """
    workspace_root = workspace_root.resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    
    if workspace_id is None:
        workspace_id = workspace_root.name
    
    if config_data is None:
        config_data = {}
    
    # Ensure project section exists with workspace_id
    if "project" not in config_data:
        config_data["project"] = {}
    config_data["project"]["workspace_id"] = workspace_id
    
    config = WorkspaceConfig(
        workspace_id=workspace_id,
        root_path=workspace_root,
        config_data=config_data
    )
    
    workspace = Workspace(config)
    workspace.save_config()
    register_workspace(workspace_id, workspace_root)
    
    return workspace


# Convenience functions for backward compatibility and common operations

def get_db_path_from_workspace_id(workspace_id: str) -> Path:
    """Get database path for a workspace ID."""
    return get_knowledge_dir() / f"{workspace_id}.db"


def get_context_path_from_workspace_id(workspace_id: str) -> Path:
    """Get active context path for a workspace ID."""
    return get_knowledge_dir() / f"{workspace_id}.context.json"


def get_current_workspace_db_path() -> Path:
    """Get database path for current workspace, with fallback."""
    workspace = load_workspace_from_current_dir()
    if workspace:
        return workspace.db_path
    # Fallback to local file
    return Path("knowledge.db")


def get_current_workspace_context_path() -> Path:
    """Get active context path for current workspace, with fallback."""
    workspace = load_workspace_from_current_dir()
    if workspace:
        return workspace.context_path
    # Fallback to local file
    return Path(".active_context.json") 