from ..core.knowledge_graph import KnowledgeGraph
from ..core.models import Node


def add_concept(kg: KnowledgeGraph, uri: str, name: str, content: str) -> Node:
    """
    Adds a new concept node to the knowledge graph.
    """
    node = Node(uri=uri, node_type="concept", name=name, content=content)
    kg.add_node(node)
    return node


def get_concept(kg: KnowledgeGraph, uri: str) -> Node | None:
    """
    Retrieves a concept node from the knowledge graph.
    """
    return kg.get_node(uri)


def update_concept(kg: KnowledgeGraph, uri: str, name: str, content: str) -> Node | None:
    """
    Updates an existing concept node in the knowledge graph.
    """
    node = kg.get_node(uri)
    if node:
        node.name = name
        node.content = content
        kg.update_node(node)
    return node


def delete_concept(kg: KnowledgeGraph, uri: str) -> bool:
    """
    Deletes a concept node from the knowledge graph.
    """
    node = kg.get_node(uri)
    if node and node.node_type == "concept":
        kg.delete_node(uri)
        return True
    return False


def move_concept(kg: KnowledgeGraph, old_uri: str, new_uri: str) -> bool:
    """
    Moves a concept from an old URI to a new URI.
    """
    node = kg.get_node(old_uri)
    if node and node.node_type == "concept":
        try:
            kg.move_node(old_uri, new_uri)
            return True
        except ValueError:
            return False
    return False 