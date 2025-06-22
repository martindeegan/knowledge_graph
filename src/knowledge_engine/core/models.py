from datetime import datetime
from typing import Literal, Any

from pydantic import BaseModel, Field


class Node(BaseModel):
    uri: str = Field(..., description="Full URI for the node, e.g., 'concept://ws/project'.")
    node_type: Literal["concept", "resource", "directory"] = Field(..., description="Type of the node.")
    name: str | None = Field(None, description="Name of the concept, null for resources.")
    content: str | None = Field(None, description="Content of the concept, null for resources.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Flexible key-value metadata.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Relation(BaseModel):
    id: int | None = Field(None, description="Primary key.")
    source_uri: str = Field(..., description="URI of the source node.")
    target_uri: str = Field(..., description="URI of the target node.")
    relation_type: str = Field(..., description="Type of the relation, e.g., 'implemented_in'.")
    weight: float = Field(1.0, description="Traversal cost (0 to 1).")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Flexible key-value metadata.")
    created_at: datetime = Field(default_factory=datetime.utcnow) 