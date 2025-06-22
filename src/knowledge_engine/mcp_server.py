#!/usr/bin/env python3
"""
Knowledge Engine MCP Server
"""
import asyncio
import logging
from functools import partial
from pathlib import Path
import threading
import uvicorn
import typer
import toml
from rich.panel import Panel
from rich.console import Console

from fastmcp import FastMCP

from .core.active_context import ActiveContext
from .core.knowledge_graph import KnowledgeGraph
from .core.config import (
    get_db_path_from_workspace_id, find_workspace_root, read_workspaces
)
from .tools import concepts, context, relations, traverse, resources
from .tools.resources import bootstrap as bootstrap_tool
from .visualization.server import app as viz_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()


class State:
    db_path: Path | None = None

state = State()


class KnowledgeEngineServer:
    """Knowledge Engine MCP Server implementation."""

    def __init__(self, viz: bool = False):
        self.mcp = FastMCP("knowledge-engine")
        if not state.db_path:
            raise ValueError("Database path not configured.")
        self.kg = KnowledgeGraph(db_path=state.db_path)
        self.ac = ActiveContext(knowledge_graph=self.kg)
        self._setup_tools()
        self.viz = viz

    def _setup_tools(self):
        """Register all available tools."""

        async def bootstrap_command_tool():
            return partial(bootstrap_tool, self.kg)()

        async def add_concept_tool(uri: str, name: str, content: str):
            return partial(concepts.add_concept, self.kg)(uri, name, content)

        async def get_concept_tool(uri: str):
            return partial(concepts.get_concept, self.kg)(uri)

        async def update_concept_tool(uri: str, name: str, content: str):
            return partial(concepts.update_concept, self.kg)(uri, name, content)

        async def delete_concept_tool(uri: str):
            return partial(concepts.delete_concept, self.kg)(uri)

        async def move_concept_tool(old_uri: str, new_uri: str):
            return partial(concepts.move_concept, self.kg)(old_uri, new_uri)

        async def delete_resource_tool(uri: str):
            return partial(resources.delete_resource, self.kg)(uri)

        async def link_nodes_tool(
            source_uri: str, target_uri: str, relation_type: str, weight: float = 1.0
        ):
            return partial(relations.link_nodes, self.kg)(
                source_uri, target_uri, relation_type, weight
            )

        async def unlink_nodes_tool(source_uri: str, target_uri: str, relation_type: str):
            return partial(relations.unlink_nodes, self.kg)(
                source_uri, target_uri, relation_type
            )

        async def get_relations_for_node_tool(uri: str):
            return partial(relations.get_relations_for_node, self.kg)(uri)

        async def get_active_context_tool():
            return partial(context.get_active_context, self.ac)()

        async def traverse_tool(start_uri: str, max_cost: float = 1.0):
            return partial(traverse.traverse, self.ac)(start_uri, max_cost)

        self.mcp.tool()(bootstrap_command_tool)
        self.mcp.tool()(add_concept_tool)
        self.mcp.tool()(get_concept_tool)
        self.mcp.tool()(update_concept_tool)
        self.mcp.tool()(delete_concept_tool)
        self.mcp.tool()(move_concept_tool)
        self.mcp.tool()(delete_resource_tool)
        self.mcp.tool()(link_nodes_tool)
        self.mcp.tool()(unlink_nodes_tool)
        self.mcp.tool()(get_relations_for_node_tool)
        self.mcp.tool()(get_active_context_tool)
        self.mcp.tool()(traverse_tool)

    async def start(self):
        """Start the MCP server."""
        if self.viz:
            self._start_viz_server()

        logger.info("Starting Knowledge Engine MCP Server...")
        await asyncio.to_thread(self.mcp.run)

    def _start_viz_server(self):
        """Starts the visualization server in a separate thread."""
        config = uvicorn.Config(viz_app, host="127.0.0.1", port=8000, log_level="info")
        server = uvicorn.Server(config)
        
        viz_thread = threading.Thread(target=server.run)
        viz_thread.daemon = True
        viz_thread.start()
        logger.info("Visualization server started at http://127.0.0.1:8000")


app = typer.Typer()

@app.command()
def main(
    viz: bool = typer.Option(False, "--viz", help="Enable the visualization server."),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Name of the workspace to use."),
):
    """Main entry point for the MCP server."""
    workspace_id = None
    workspace_root_path = "N/A"

    if workspace:
        state.db_path = get_db_path_from_workspace_id(workspace)
        if not state.db_path.exists():
            logger.error(f"Workspace '{workspace}' not found at {state.db_path}")
            raise typer.Abort()
        workspace_id = workspace
        workspaces_meta = read_workspaces()
        workspace_root_path = workspaces_meta.get(workspace, {}).get("root_path", "N/A")
    else:
        workspace_root = find_workspace_root()
        if not workspace_root:
            logger.error("Not inside a Knowledge Engine workspace.")
            raise typer.Abort()
        
        workspace_root_path = str(workspace_root.resolve())
        config_path = workspace_root / "ke_config.toml"
        with open(config_path, "r") as f:
            config = toml.load(f)
            workspace_id = config.get("project", {}).get("workspace_id")
            if not workspace_id:
                logger.error(f"Workspace ID not found in {config_path}")
                raise typer.Abort()
            state.db_path = get_db_path_from_workspace_id(workspace_id)

    message = (
        f"[bold]Workspace ID:[/]    {workspace_id}\n"
        f"[bold]Root Path:[/]       {workspace_root_path}\n"
        f"[bold]Database Path:[/]   {state.db_path}"
    )

    panel = Panel(
        message,
        title="[bold cyan]Knowledge Engine Workspace[/bold cyan]",
        expand=False,
        border_style="green"
    )
    console.print(panel)

    server = KnowledgeEngineServer(viz=viz)
    asyncio.run(server.start())


if __name__ == "__main__":
    app()