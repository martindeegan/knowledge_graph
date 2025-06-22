#!/usr/bin/env python3
"""
Visualization server for the Knowledge Engine.
"""
import logging
import sys
from pathlib import Path
from importlib.util import find_spec
import toml
import asyncio
from typing import Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core.active_context import ActiveContext
from ..core.knowledge_graph import KnowledgeGraph
from ..core.workspace import Workspace

# Configure logging to stderr for visualization server
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NavigateRequest(BaseModel):
    uri: str
    max_cost: float = 1.0

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket client: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)

# Global WebSocket manager
ws_manager = WebSocketManager()

def create_app(mcp_app, workspace: Workspace) -> FastAPI:
    """Create and configure the visualization FastAPI app."""
    
    app = FastAPI(title="Knowledge Engine Server",
        description="Knowledge Engine Server with Live Graph Visualization",
        version="1.0.0",
        lifespan=mcp_app.lifespan
    )
    
    # Add CORS middleware for cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    def create_kg():
        """Create a new knowledge graph instance."""
        return KnowledgeGraph(db_path=workspace.db_path)

    def get_active_context():
        """Get the singleton active context instance."""
        return ActiveContext.get_instance()

    # Mount static files
    spec = find_spec("knowledge_engine.server")
    if spec and spec.origin:
        static_dir = Path(spec.origin).parent / "static"
    else:
        static_dir = Path(__file__).parent / "static"
    
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/viz")
    async def viz_index():
        """Serve the visualization index page."""
        return FileResponse(static_dir / "index.html")

    # REST API Endpoints
    @app.get("/api/graph")
    async def api_get_graph_data():
        """Get the current active context graph data."""
        try:
            # Use the shared active context directly (same thread, no issues)
            ac = get_active_context()
            kg = create_kg()
            nodes = ac.list_nodes(kg)
            
            node_uris = [node.uri for node in nodes]
            relations = kg.get_relations_for_nodes(node_uris)
            
            graph_data = {
                "nodes": [node.model_dump(mode='json') for node in nodes],
                "relations": [relation.model_dump(mode='json') for relation in relations],
                "stats": {
                    "total_nodes": kg.get_node_count(),
                    "total_relations": kg.get_relation_count(),
                    "active_nodes": len(nodes),
                    "active_relations": len(relations)
                }
            }
            
            return JSONResponse(graph_data)
        except Exception as e:
            logger.error(f"Error in api_get_graph_data: {e}")
            return JSONResponse({"nodes": [], "relations": [], "stats": {}})

    @app.post("/api/navigate")
    async def api_navigate_to_node(request: NavigateRequest):
        """Navigate to a node and add traversed nodes to active context."""
        try:
            ac = get_active_context()
            kg = create_kg()
            old_node_count = len(ac.list_nodes(kg))
            
            nodes = ac.traverse(request.uri, kg, request.max_cost)
            
            if nodes:
                new_node_count = len(ac.list_nodes(kg))
                added_nodes = new_node_count - old_node_count
                
                # Broadcast the graph update to WebSocket clients
                graph_data = await get_graph_update_data()
                await ws_manager.broadcast({
                    "type": "graph_update",
                    "data": graph_data
                })
                
                # Also broadcast navigation event
                await ws_manager.broadcast({
                    "type": "navigation_complete",
                    "data": {
                        "uri": request.uri,
                        "nodes_added": added_nodes,
                        "message": f"Traversal from '{request.uri}' complete. {added_nodes} new nodes added to context."
                    }
                })
                
                return JSONResponse({
                    "success": True,
                    "message": f"Traversal from '{request.uri}' complete. {added_nodes} new nodes added to context.",
                    "nodes_added": added_nodes
                })
            else:
                return JSONResponse({
                    "success": False,
                    "error": "Start node not found for traversal."
                }, status_code=404)
        except Exception as e:
            logger.error(f"Error in api_navigate_to_node: {e}")
            return JSONResponse({
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }, status_code=500)

    @app.get("/api/node/{uri:path}")
    async def api_get_node(uri: str):
        """Get detailed information about a specific node."""
        try:
            kg = create_kg()
            node = kg.get_node(uri)
            
            if not node:
                return JSONResponse({
                    "error": f"Node not found: {uri}"
                }, status_code=404)
            
            # Get relations for this node
            relations = kg.get_relations(source_uri=uri) + kg.get_relations(target_uri=uri)
            
            return JSONResponse({
                "node": node.model_dump(mode='json'),
                "relations": [relation.model_dump(mode='json') for relation in relations],
                "relation_count": len(relations)
            })
        except Exception as e:
            logger.error(f"Error getting node {uri}: {e}")
            return JSONResponse({
                "error": f"Internal server error: {str(e)}"
            }, status_code=500)

    @app.get("/api/stats")
    async def api_get_stats():
        """Get overall knowledge graph statistics."""
        try:
            kg = create_kg()
            ac = get_active_context()
            
            active_nodes = ac.list_nodes(kg)
            node_uris = [node.uri for node in active_nodes]
            active_relations = kg.get_relations_for_nodes(node_uris)
            
            return JSONResponse({
                "total_nodes": kg.get_node_count(),
                "total_relations": kg.get_relation_count(),
                "active_nodes": len(active_nodes),
                "active_relations": len(active_relations),
                "workspace_id": workspace.id
            })
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return JSONResponse({"error": f"Internal server error: {str(e)}"}, status_code=500)

    # WebSocket endpoint for real-time updates
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time graph updates."""
        await ws_manager.connect(websocket)
        try:
            # Send initial graph data
            graph_data = await get_graph_update_data()
            await websocket.send_json({
                "type": "initial_data",
                "data": graph_data
            })
            
            # Keep connection alive and handle client messages
            while True:
                try:
                    data = await websocket.receive_json()
                    
                    # Handle different message types from client
                    if data.get("type") == "navigate":
                        uri = data.get("uri")
                        max_cost = data.get("max_cost", 1.0)
                        if uri:
                            request = NavigateRequest(uri=uri, max_cost=max_cost)
                            result = await api_navigate_to_node(request)
                            await websocket.send_json({
                                "type": "navigation_result",
                                "data": result
                            })
                    elif data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                        
                except Exception as e:
                    logger.warning(f"Error processing WebSocket message: {e}")
                    break
                    
        except WebSocketDisconnect:
            pass
        finally:
            ws_manager.disconnect(websocket)
    
    async def get_graph_update_data():
        """Helper function to get current graph data for broadcasting."""
        try:
            ac = get_active_context()
            kg = create_kg()
            nodes = ac.list_nodes(kg)
            
            node_uris = [node.uri for node in nodes]
            relations = kg.get_relations_for_nodes(node_uris)
            
            return {
                "nodes": [node.model_dump(mode='json') for node in nodes],
                "relations": [relation.model_dump(mode='json') for relation in relations],
                "stats": {
                    "total_nodes": kg.get_node_count(),
                    "total_relations": kg.get_relation_count(),
                    "active_nodes": len(nodes),
                    "active_relations": len(relations)
                }
            }
        except Exception as e:
            logger.error(f"Error getting graph update data: {e}")
            return {"nodes": [], "relations": [], "stats": {}}

    # Legacy endpoints for backward compatibility
    @app.get("/viz/api/graph")
    async def viz_get_graph_data():
        """Legacy endpoint - redirects to new API."""
        return await api_get_graph_data()

    @app.post("/viz/api/navigate")
    async def viz_navigate_to_node(request: NavigateRequest):
        """Legacy endpoint - redirects to new API."""
        return await api_navigate_to_node(request)

    return app