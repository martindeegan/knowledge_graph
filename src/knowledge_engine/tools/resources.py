#!/usr/bin/env python3
"""
Tools for managing resources in the Knowledge Graph.
"""

from pathlib import Path
import os
import tomllib
from datetime import datetime
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
import fnmatch

from ..core.knowledge_graph import KnowledgeGraph
from ..core.models import Node, Relation

DEFAULT_IGNORE_DIRS = {".git", "__pycache__", ".vscode", ".idea", "node_modules", "build", "dist", ".venv"}

def bootstrap(kg: KnowledgeGraph, root_path: str | Path = ".") -> None:
    """
    Scans a directory and adds all files and subdirectories to the knowledge graph.
    Reads ignore patterns from a ke_config.toml file if it exists.
    """
    console = Console()
    root_path = Path(root_path).resolve()
    config_path = root_path / "ke_config.toml"
    
    ignore_dirs = DEFAULT_IGNORE_DIRS
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
            ignore_dirs.update(config.get("bootstrap", {}).get("ignore_dirs", []))

    gitignore_path = root_path / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ignore_dirs.add(line)

    log_group = Group()
    with Live(Panel(log_group, title="[bold green]Bootstrapping...[/]", border_style="green"), console=console, screen=False) as live:
        for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
            # Filter out ignored directories
            original_dirnames = list(dirnames)
            dirnames[:] = [d for d in original_dirnames if not any(fnmatch.fnmatch(d, pattern) for pattern in ignore_dirs)]
            
            # Also need to filter filenames
            filenames[:] = [f for f in filenames if not any(fnmatch.fnmatch(f, pattern) for pattern in ignore_dirs)]

            current_dir_path = Path(dirpath)
            relative_dir_path = current_dir_path.relative_to(root_path)

            log_group.renderables.append(
                Text(f"Scanning {relative_dir_path.as_posix()}", style="cyan")
            )
            
            # Keep the log group from getting too long
            if len(log_group.renderables) > 15:
                log_group.renderables.pop(0)

            live.update(Panel(log_group, title="[bold green]Bootstrapping...[/]", border_style="green"))

            # Create or get directory node
            dir_uri = f"dir://{relative_dir_path.as_posix()}"
            if not kg.get_node(dir_uri):
                dir_node = Node(uri=dir_uri, node_type="directory", name=current_dir_path.name, content=None)
                kg.add_node(dir_node)

            # Link to parent directory
            if current_dir_path != root_path:
                parent_dir_path = relative_dir_path.parent
                parent_uri = f"dir://{parent_dir_path.as_posix()}"
                relation = Relation(id=None, source_uri=parent_uri, target_uri=dir_uri, relation_type="contains", weight=1.0, metadata={}, created_at=datetime.utcnow())
                kg.add_relation(relation)

            for filename in filenames:
                file_path = current_dir_path / filename
                relative_file_path = file_path.relative_to(root_path)
                file_uri = f"file://{relative_file_path.as_posix()}"

                if not kg.get_node(file_uri):
                    file_node = Node(uri=file_uri, node_type="resource", name=filename, content=None)
                    kg.add_node(file_node)
                    relation = Relation(id=None, source_uri=dir_uri, target_uri=file_uri, relation_type="contains", weight=1.0, metadata={}, created_at=datetime.utcnow())
                    kg.add_relation(relation)

def delete_resource(kg: KnowledgeGraph, uri: str) -> bool:
    """
    Deletes a resource node from the knowledge graph.
    """
    node = kg.get_node(uri)
    if node and (node.node_type == "resource" or node.node_type == "directory"):
        kg.delete_node(uri)
        return True
    return False 