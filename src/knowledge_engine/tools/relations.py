from ..core.knowledge_graph import KnowledgeGraph
from ..core.models import Relation


def link_nodes(
    kg: KnowledgeGraph,
    source_uri: str,
    target_uri: str,
    relation_type: str,
    weight: float = 1.0,
) -> Relation:
    """
    Creates a new relation between two nodes.
    """
    relation = Relation(
        id=None,
        source_uri=source_uri,
        target_uri=target_uri,
        relation_type=relation_type,
        weight=weight,
    )
    relation_id = kg.add_relation(relation)
    relation.id = relation_id
    return relation


def unlink_nodes(
    kg: KnowledgeGraph,
    source_uri: str,
    target_uri: str,
    relation_type: str,
) -> None:
    """
    Deletes a relation between two nodes.
    """
    kg.delete_relation_by_uris_and_type(source_uri, target_uri, relation_type)


def get_relations_for_node(kg: KnowledgeGraph, uri: str) -> list[Relation]:
    """
    Retrieves all incoming and outgoing relations for a given node.
    """
    outgoing = kg.get_relations(source_uri=uri)
    incoming = kg.get_relations(target_uri=uri)
    return outgoing + incoming 