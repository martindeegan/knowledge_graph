#!/usr/bin/env python3
"""
Main Knowledge Engine Server that combines MCP and Visualization servers.
"""
import logging
import sys
import socket
import subprocess
import platform
import psutil
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
import typer
import uvicorn
from fastmcp import FastMCP
from fastapi import FastAPI

from knowledge_engine.core.active_context import ActiveContext
from knowledge_engine.core.knowledge_graph import KnowledgeGraph
from knowledge_engine.core.workspace import load_workspace
from knowledge_engine.server.mcp_server import create_mcp_server
from knowledge_engine.server.server import create_app

# Set up logging to stderr to avoid interfering with MCP JSON-RPC on stdout
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # Override any existing logging configuration
)


def kill_process_on_port(port: int) -> bool:
    """
    Kill any process currently using the specified port.
    
    Args:
        port (int): The port number to check and clear.
        
    Returns:
        bool: True if a process was found and killed, False if no process was using the port.
    """
    try:
        # Find processes using the port
        processes_killed = []
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # Get connections by calling the connections() method
                connections = proc.connections(kind='inet')
                if connections:
                    for conn in connections:
                        if (conn.laddr.port == port and 
                            conn.status in [psutil.CONN_LISTEN, psutil.CONN_ESTABLISHED]):
                            
                            pid = proc.info['pid']
                            name = proc.info['name']
                            
                            logging.info(f"Found process using port {port}: {name} (PID: {pid})")
                            
                            try:
                                # Try to terminate gracefully first
                                proc.terminate()
                                proc.wait(timeout=3)
                                processes_killed.append(f"{name} (PID: {pid})")
                                logging.info(f"Gracefully terminated process {name} (PID: {pid})")
                            except psutil.TimeoutExpired:
                                # Force kill if graceful termination fails
                                proc.kill()
                                processes_killed.append(f"{name} (PID: {pid}) - force killed")
                                logging.info(f"Force killed process {name} (PID: {pid})")
                            except psutil.NoSuchProcess:
                                # Process already died
                                pass
                            except psutil.AccessDenied:
                                logging.warning(f"Access denied when trying to kill process {name} (PID: {pid})")
                                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process disappeared or we don't have access
                continue
        
        if processes_killed:
            logging.info(f"Killed {len(processes_killed)} process(es) using port {port}: {', '.join(processes_killed)}")
            return True
        else:
            logging.debug(f"No processes found using port {port}")
            return False
            
    except Exception as e:
        logging.error(f"Error while checking/killing processes on port {port}: {e}")
        return False


def find_available_port(start_port=8000, max_attempts=100):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts}")

def display_server_info(workspace, viz_enabled=False, viz_url=None):
    """Display server startup information in a nice panel to stderr."""
    # Use stderr to avoid interfering with MCP JSON-RPC on stdout
    console = Console(file=sys.stderr)
    
    # Create a temporary kg instance to get counts
    try:
        temp_kg = KnowledgeGraph(db_path=workspace.db_path)
        node_count = temp_kg.get_node_count()
        relation_count = temp_kg.get_relation_count()
    except Exception:
        node_count = 0
        relation_count = 0
    
    info_lines = [
        f"[bold]Workspace:[/] {workspace.id}",
        f"[bold]Location:[/] {workspace.root}",
        f"[bold]Database:[/] {workspace.db_path}",
        "",
        f"[bold]Nodes:[/] {node_count}",
        f"[bold]Relations:[/] {relation_count}",
        "",
        "[bold cyan]Available Endpoints:[/]",
    ]
    
    if viz_enabled and viz_url:
        # HTTP mode with visualization
        info_lines.extend([
            f"  [green]Root:[/] {viz_url}/",
            f"  [green]Health:[/] {viz_url}/health",
            f"  [green]MCP:[/] {viz_url}/mcp-server/mcp",
            f"  [green]Visualization:[/] {viz_url}/viz"
        ])
    else:
        # STDIO mode - show what would be available in HTTP mode
        info_lines.extend([
            f"  [yellow]MCP:[/] STDIO mode (current)",
            f"  [dim]To enable HTTP endpoints, run with:[/]",
            f"  [dim]  --http[/]"
        ])
    
    panel = Panel(
        "\n".join(info_lines),
        title="[bold cyan]Knowledge Engine Server[/bold cyan]",
        expand=False,
        border_style="green"
    )
    console.print(panel)

def initialize_workspace(workspace_name=None):
    """Initialize the workspace components."""
    workspace = load_workspace(workspace_name)
    if not workspace:
        if workspace_name:
            raise ValueError(f"Workspace '{workspace_name}' not found.")
        else:
            raise ValueError("No workspace found. Please run from within a workspace directory or specify --workspace.")

    # Initialize global active context singleton with root nodes
    ac = ActiveContext.get_instance()
    kg = KnowledgeGraph(db_path=workspace.db_path)
    ac.initialize_with_root_nodes(kg, workspace)
    
    return workspace

def create_combined_server(workspace, port):
    """Create a combined server with MCP and visualization."""
    
    # Create your FastMCP server as well as any tools, resources, etc.
    mcp = create_mcp_server(workspace.root, workspace.id, workspace.db_path)
    # Create the ASGI app (Streamable HTTP transport is default)
    mcp_app = mcp.http_app(path='/mcp')
    
    # Create the app with visualization endpoints
    app = create_app(mcp_app, workspace)
    
    # Mount the MCP app
    app.mount("/mcp-server", mcp_app, name="mcp")
    
    # Add root endpoint showing available services
    @app.get("/")
    async def root():
        endpoints = {
            "mcp": "/mcp-server/mcp",
            "health": "/health"
        }
        
        return {
            "message": "Knowledge Engine Master Server",
            "workspace_id": workspace.id,
            "endpoints": endpoints
        }
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "workspace_id": workspace.id}
    
    logging.info("Created master server with MCP mounted at /mcp-server/mcp")
    logging.info("Visualization mounted at /viz")
    
    return app

def run_server(
    workspace_name: Optional[str] = typer.Option(
        None, 
        "--workspace", 
        help="Workspace directory name or path"
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        help="Port to run the server on (default: auto-find available port)"
    )
):
    """
    Knowledge Engine Server - Provides MCP and visualization services.
    
    Examples:
        # STDIO mode for Claude Desktop
        python server.py --workspace myproject --stdio
        
        # HTTP mode for development
        python server.py --workspace myproject --port 8000
    """
    try:
        logging.info("Starting server initialization...")
        
        # Initialize workspace
        logging.info(f"Initializing workspace: {workspace_name}")
        workspace = initialize_workspace(workspace_name)
        logging.info(f"Workspace initialized: {workspace.id} at {workspace.root}")

        # HTTP mode for development/testing
        logging.info("Running in HTTP mode...")
        app = create_combined_server(workspace, port)
        logging.info("Combined server created with MCP and visualization")
        
        # Run the combined server via HTTP
        if port is None:
            port = find_available_port()
            logging.info(f"Auto-selected port: {port}")
        else:
            logging.info(f"Using specified port: {port}")
            # Kill any existing processes on the specified port
            logging.info(f"Checking for existing processes on port {port}...")
            kill_process_on_port(port)
        
        host = "127.0.0.1"
        server_url = f"http://{host}:{port}"
        display_server_info(workspace, True, server_url)
        
        logging.info("Starting uvicorn server...")
        
        # Suppress uvicorn's default logging to avoid JSON parsing issues with Claude Desktop
        uvicorn.run(
            app, 
            host=host, 
            port=port, 
            log_level="error",  # Only show errors, not info messages
            access_log=False,   # Disable access logging
            use_colors=False    # Disable colored output
        )
        
        logging.info("Server stopped normally")
        
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        logging.exception("Full exception details:")
        raise typer.Exit(1)


def main():
    typer.run(run_server)

if __name__ == "__main__":
    main()