#!/usr/bin/env python3
"""
Visualization server for the Knowledge Engine.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import toml

from knowledge_engine.core.knowledge_graph import KnowledgeGraph
from knowledge_engine.core.active_context import ActiveContext

app = FastAPI()

class NavigateRequest(BaseModel):
    uri: str
    max_cost: float = 1.0

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def _get_db_path() -> Path:
    """
    Determines the database path based on ke_config.toml or defaults.
    """
    config_path = Path("ke_config.toml")
    if config_path.exists():
        with open(config_path, "r") as f:
            config = toml.load(f)
            workspace_id = config.get("project", {}).get("workspace_id")
            if workspace_id:
                db_dir = Path.home() / ".knowledge"
                return db_dir / f"{workspace_id}.db"
    # This fallback is for when the server is run without a workspace context
    return Path("knowledge.db")

def get_kg():
    db_path = _get_db_path()
    return KnowledgeGraph(db_path=db_path)

@app.get("/api/graph")
async def get_graph_data():
    """
    Returns the current ActiveContext graph data.
    """
    kg = get_kg()
    ac = ActiveContext(kg)
    
    nodes = ac.list_nodes()
    node_uris = [node.uri for node in nodes]
    
    relations = kg.get_relations_for_nodes(node_uris)
    
    # Pydantic models need to be converted to dicts for JSON serialization
    return {
        "nodes": [node.model_dump() for node in nodes],
        "relations": [relation.model_dump() for relation in relations],
    }

@app.post("/api/navigate")
async def navigate_to_node(request: NavigateRequest):
    """
    Traverses from the given URI and adds resulting nodes to the active context.
    """
    kg = get_kg()
    ac = ActiveContext(kg)
    nodes = ac.traverse(request.uri, request.max_cost)
    if nodes:
        return {"message": f"Traversal from '{request.uri}' complete. {len(nodes)} nodes added to context."}
    else:
        raise HTTPException(status_code=404, detail="Start node not found for traversal.")

@app.get("/")
async def read_index():
    """
    Serves the main index.html file.
    """
    return FileResponse(static_dir / "index.html") 