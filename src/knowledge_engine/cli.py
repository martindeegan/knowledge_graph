#!/usr/bin/env python3
"""
Command-line interface for managing the Knowledge Engine.
"""
import typer
from pathlib import Path
import toml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import os

from .core.knowledge_graph import KnowledgeGraph
from .tools.resources import bootstrap as bootstrap_tool
from .core.config import (
    get_db_path, get_context_path, find_workspace_root, 
    get_db_path_from_workspace_id, register_workspace
)
from .tools import concepts as concepts_tool, relations as relations_tool
from .core.active_context import ActiveContext

app = typer.Typer()
console = Console()

context_app = typer.Typer(help="Manage the active context.")
app.add_typer(context_app, name="context")

class State:
    db_path: Path | None = None

state = State()

@app.callback()
def main_callback(ctx: typer.Context):
    """
    Knowledge Engine CLI
    """
    # The init command does not require a workspace, so we skip the check for it.
    if ctx.invoked_subcommand == 'init':
        return
    
    # For other commands, we'll handle workspace logic within the command itself.
    pass


_kg = None
def get_kg(workspace: str | None = None):
    global _kg
    if _kg is None:
        if workspace:
            db_path = get_db_path_from_workspace_id(workspace)
            if not db_path.exists():
                console.print(f"[bold red]Error:[/] Workspace '{workspace}' not found at {db_path}")
                raise typer.Abort()
            state.db_path = db_path
        else:
            workspace_root = find_workspace_root()
            if not workspace_root:
                console.print("[bold red]Error:[/] Not inside a Knowledge Engine workspace.")
                console.print("Please run `ke-cli init` or specify a workspace with `--workspace`.")
                raise typer.Abort()
            
            config_path = workspace_root / "ke_config.toml"
            with open(config_path, "r") as f:
                config = toml.load(f)
                workspace_id = config.get("project", {}).get("workspace_id")
                if not workspace_id:
                    console.print(f"[bold red]Error:[/] Workspace ID not found in {config_path}")
                    raise typer.Abort()
                state.db_path = get_db_path_from_workspace_id(workspace_id)

        if state.db_path is None:
            # This should not happen due to the logic above, but as a safeguard:
            console.print("[bold red]Error:[/] Database path not configured.")
            raise typer.Abort()
        _kg = KnowledgeGraph(db_path=state.db_path)
    return _kg

_ac = None
def get_ac():
    global _ac
    if _ac is None:
        if _kg is None:
            # get_kg() must be called first
            raise typer.Abort("KnowledgeGraph not initialized.")
        _ac = ActiveContext(_kg)
    return _ac

@app.command()
def info(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Name of the workspace to use.")
):
    """
    Displays information about the current workspace.
    """
    kg = get_kg(workspace)
    if not state.db_path:
        console.print("[bold red]Error:[/] Could not determine database path.")
        raise typer.Abort()

    context_path = get_context_path()
    
    node_count = kg.get_node_count()
    relation_count = kg.get_relation_count()

    message = (
        f"[bold]Database Path:[/] {state.db_path.resolve()}\n"
        f"[bold]Context Path:[/]  {context_path.resolve()}\n\n"
        f"[bold]Nodes:[/]         {node_count}\n"
        f"[bold]Relations:[/]     {relation_count}"
    )

    panel = Panel(
        message,
        title="[bold cyan]Knowledge Engine Status[/bold cyan]",
        expand=False,
        border_style="green"
    )
    console.print(panel)

@app.command()
def init(workspace_name: str | None = typer.Argument(None, help="Name for the new workspace. Defaults to the current directory name.")):
    """
    Initializes a new workspace config. Fails if a workspace is already configured.
    """
    if workspace_name is None:
        workspace_name = Path.cwd().name
        console.print(f"No workspace name provided. Using current directory name: [bold cyan]{workspace_name}[/bold cyan]")

    config_path = Path("ke_config.toml")

    # Check for existing workspace config
    if config_path.exists():
        with open(config_path, "r") as f:
            existing_config = toml.load(f)
            if existing_config.get("project", {}).get("workspace_id"):
                console.print(f"[bold red]Error:[/] A workspace is already initialized in {config_path.resolve()}.")
                console.print("To create a new workspace, either remove the old one or run `init` in a different directory.")
                raise typer.Abort()

    # Initialize home directory
    db_dir = Path.home() / ".knowledge"
    if not db_dir.exists():
        console.print(f"Creating knowledge engine home directory at: {db_dir}")
        db_dir.mkdir(parents=True)
    else:
        console.print(f"Knowledge engine home directory already exists at: {db_dir}")

    # Initialize workspace config
    config = {}
    if config_path.exists():
        with open(config_path, "r") as f:
            config = toml.load(f)
    
    if "project" not in config:
        config["project"] = {}
    config["project"]["workspace_id"] = workspace_name

    if "bootstrap" not in config:
        config["bootstrap"] = {
            "ignore_dirs": [
                ".git", ".venv", "__pycache__", ".vscode", ".idea", 
                "node_modules", "build", "dist", "*.egg-info"
            ]
        }
    
    with open(config_path, "w", encoding="utf-8") as f:
        toml.dump(config, f)
    
    # Register the workspace globally
    register_workspace(workspace_name, Path.cwd())
    
    console.print(f"Workspace '{workspace_name}' initialized and registered.")

    console.print("\nRunning initial bootstrap...")
    db_path = get_db_path_from_workspace_id(workspace_name)
    kg = KnowledgeGraph(db_path=db_path)
    bootstrap_tool(kg, ".")
    console.print("Bootstrap complete.")

    console.print("Adding project root concept...")
    project_concept_uri = f"concept://{workspace_name}/project"
    concepts_tool.add_concept(
        kg,
        uri=project_concept_uri,
        name="Project Root",
        content=f"Root concept for the {workspace_name} project.",
    )

    relations_tool.link_nodes(
        kg,
        source_uri=project_concept_uri,
        target_uri="dir://.",
        relation_type="represents",
    )
    console.print("Project root concept linked to root directory.")

@app.command()
def bootstrap(
    root: str = typer.Option(".", "--root", "-r", help="Root directory to start bootstrap from."),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Name of the workspace to use.")
):
    """
    Scans the project and adds all files to the knowledge graph.
    """
    kg = get_kg(workspace)
    console.print(f"Starting bootstrap from: {root}")
    bootstrap_tool(kg, root)
    console.print("Bootstrap complete.")

@app.command(name="add-concept")
def add_concept(
    uri: str = typer.Argument(..., help="URI for the new concept."),
    name: str = typer.Argument(..., help="Name of the new concept."),
    content: str = typer.Argument(..., help="Content/description of the new concept."),
):
    """
    Adds a new concept to the knowledge graph.
    """
    kg = get_kg()
    concepts_tool.add_concept(kg, uri, name, content)
    console.print(f"Concept '{uri}' added.")

@app.command(name="get-concept")
def get_concept(uri: str = typer.Argument(..., help="URI of the concept to retrieve.")):
    """
    Retrieves and displays a concept from the knowledge graph.
    """
    kg = get_kg()
    node = concepts_tool.get_concept(kg, uri)
    if node:
        console.print(f"URI: {node.uri}")
        console.print(f"Name: {node.name}")
        console.print(f"Type: {node.node_type}")
        console.print(f"Content: {node.content}")
    else:
        console.print(f"Concept '{uri}' not found.")

@app.command(name="update-concept")
def update_concept(
    uri: str = typer.Argument(..., help="URI of the concept to update."),
    name: str = typer.Option(None, "--name", "-n", help="New name for the concept."),
    content: str = typer.Option(None, "--content", "-c", help="New content for the concept."),
):
    """
    Updates an existing concept in the knowledge graph.
    """
    kg = get_kg()
    original_node = concepts_tool.get_concept(kg, uri)
    if not original_node:
        console.print(f"Concept '{uri}' not found.")
        raise typer.Abort()

    new_name = name if name is not None else original_node.name
    new_content = content if content is not None else original_node.content

    concepts_tool.update_concept(kg, uri, new_name, new_content)
    console.print(f"Concept '{uri}' updated.")

@app.command(name="link-nodes")
def link_nodes(
    source_uri: str = typer.Argument(..., help="Source URI of the relation."),
    target_uri: str = typer.Argument(..., help="Target URI of the relation."),
    relation_type: str = typer.Argument(..., help="Type of the relation."),
    weight: float = typer.Option(1.0, help="Weight of the relation."),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Name of the workspace to use.")
):
    """
    Adds a new relation to the knowledge graph.
    """
    kg = get_kg(workspace)
    relations_tool.link_nodes(kg, source_uri, target_uri, relation_type, weight)
    console.print(f"Relation '{source_uri} -> {target_uri}' of type '{relation_type}' added.")

@app.command()
def clear(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Name of the workspace to use.")
):
    """
    Clears all data from the knowledge graph.
    """
    if not yes:
        if not typer.confirm("Are you sure you want to delete all data in the knowledge graph?"):
            raise typer.Abort()
    
    kg = get_kg(workspace)
    kg.clear_graph()
    console.print("Knowledge graph cleared.")

@app.command()
def show(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Name of the workspace to use.")
):
    """
    Shows all nodes and relations in the knowledge graph.
    """
    kg = get_kg(workspace)
    nodes, relations = kg.get_all_nodes_and_relations()

    node_table = Table(title="Nodes")
    node_table.add_column("URI", style="cyan")
    node_table.add_column("Type", style="magenta")
    node_table.add_column("Name", style="green")

    for node in nodes:
        node_table.add_row(node.uri, node.node_type, node.name)

    relation_table = Table(title="Relations")
    relation_table.add_column("Source URI", style="cyan")
    relation_table.add_column("Target URI", style="cyan")
    relation_table.add_column("Type", style="magenta")
    relation_table.add_column("Weight", style="yellow")

    for relation in relations:
        relation_table.add_row(
            relation.source_uri,
            relation.target_uri,
            relation.relation_type,
            str(relation.weight),
        )

    console.print(node_table)
    console.print(relation_table)

@context_app.command("show")
def show_context():
    """
    Shows all nodes in the active context.
    """
    ac = get_ac()
    nodes = ac.list_nodes()

    table = Table(title="Active Context")
    table.add_column("URI", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Name", style="green")

    for node in nodes:
        table.add_row(node.uri, node.node_type, node.name)

    console.print(table)

@context_app.command("add")
def add_to_context(uri: str = typer.Argument(..., help="URI of the node to add.")):
    """
    Adds a node to the active context.
    """
    ac = get_ac()
    node = ac.get(uri)
    if node:
        console.print(f"Node '{uri}' added to active context.")
    else:
        console.print(f"Node '{uri}' not found in knowledge graph.")

@context_app.command("traverse")
def traverse_context(
    start_uri: str = typer.Argument(..., help="URI of the node to start traversal from."),
    max_cost: float = typer.Option(1.0, help="Maximum cost for traversal.")
):
    """
    Traverses the graph from a starting node and adds results to the context.
    """
    ac = get_ac()
    nodes = ac.traverse(start_uri, max_cost)
    if nodes:
        console.print(f"Traversal from '{start_uri}' complete. {len(nodes)} nodes added to context.")
    else:
        console.print(f"No nodes found in traversal from '{start_uri}' or start node not found.")

@context_app.command("clear")
def clear_context():
    """
    Clears all nodes from the active context.
    """
    ac = get_ac()
    ac.clear()
    console.print("Active context cleared.")

if __name__ == "__main__":
    app() 