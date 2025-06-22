from ..core.active_context import ActiveContext
from ..core.models import Node


def traverse(ac: ActiveContext, start_uri: str, max_cost: float = 1.0) -> list[Node]:
    """
    Traverses the knowledge graph from a starting node, adding nodes to the
    Active Context based on a maximum traversal cost.
    """
    return ac.traverse(start_uri, max_cost) 