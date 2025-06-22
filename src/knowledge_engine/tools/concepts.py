import re
from ..core.knowledge_graph import KnowledgeGraph
from ..core.models import Node, Relation
from ..core.active_context import ActiveContext


def _extract_concept_links(content: str) -> list[str]:
    """
    Extract concept URIs from markdown links in the content.
    
    Looks for patterns like [text](concept://uri) and returns the concept URIs.
    """
    if not content:
        return []
    
    # Pattern to match markdown links with concept:// URIs
    pattern = r'\[([^\]]+)\]\((concept://[^)]+)\)'
    matches = re.findall(pattern, content)
    
    # Return just the URIs (second group from each match)
    return [uri for text, uri in matches]


def _create_concept_links(kg: KnowledgeGraph, source_uri: str, linked_uris: list[str]):
    """
    Create relationships between a source concept and concepts it links to.
    
    Creates 'references' relationships from source to linked concepts.
    """
    for target_uri in linked_uris:
        # Check if the target concept exists
        if kg.get_node(target_uri):
            # Create a 'references' relationship
            relation = Relation(
                id=None,
                source_uri=source_uri,
                target_uri=target_uri,
                relation_type="references",
                weight=0.3,  # Medium weight for reference links
                metadata={
                    "auto_generated": True,
                    "link_type": "markdown_reference"
                }
            )
            kg.add_relation(relation)


def add_concept(kg: KnowledgeGraph, uri: str, name: str, content: str) -> Node:
    """
    Adds a new concept node to the knowledge graph.
    
    Automatically creates relationships to other concepts referenced in markdown links
    and adds the new concept to the active context for immediate availability.
    """
    node = Node(uri=uri, node_type="concept", name=name, content=content)
    kg.add_node(node)
    
    # Extract and create links to referenced concepts
    linked_uris = _extract_concept_links(content)
    if linked_uris:
        _create_concept_links(kg, uri, linked_uris)
    
    # Add the newly created concept to the active context
    try:
        ac = ActiveContext.get_instance()
        ac.add(node)
    except Exception as e:
        # Log the error but don't fail the concept creation
        # This allows the function to work even if active context is not available
        import logging
        logging.warning(f"Failed to add concept {uri} to active context: {e}")
    
    return node


def get_concept(kg: KnowledgeGraph, uri: str) -> Node | None:
    """
    Retrieves a concept node from the knowledge graph.
    """
    return kg.get_node(uri)


def update_concept(kg: KnowledgeGraph, uri: str, name: str, content: str) -> Node | None:
    """
    Updates an existing concept node in the knowledge graph.
    
    Automatically updates relationships to other concepts referenced in markdown links
    and refreshes the concept in the active context if it's already there.
    """
    node = kg.get_node(uri)
    if node:
        # Remove existing auto-generated reference links
        existing_relations = kg.get_relations(source_uri=uri)
        for relation in existing_relations:
            if (relation.relation_type == "references" and 
                relation.metadata.get("auto_generated") and
                relation.metadata.get("link_type") == "markdown_reference" and
                relation.id is not None):
                kg.delete_relation(relation.id)
        
        # Update the node
        node.name = name
        node.content = content
        kg.update_node(node)
        
        # Create new links based on updated content
        linked_uris = _extract_concept_links(content)
        if linked_uris:
            _create_concept_links(kg, uri, linked_uris)
        
        # Update the concept in active context if it exists there
        try:
            ac = ActiveContext.get_instance()
            # Adding the updated node will refresh it in the active context
            ac.add(node)
        except Exception as e:
            # Log the error but don't fail the concept update
            import logging
            logging.warning(f"Failed to update concept {uri} in active context: {e}")
    
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