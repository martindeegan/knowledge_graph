import json
from collections import deque
from typing import OrderedDict, Optional
from pathlib import Path

from .knowledge_graph import KnowledgeGraph
from .models import Node
from .config import get_context_path


class ActiveContext:
    _instance = None
    _initialized = False
    
    def __new__(cls, max_size: int = 100):
        if cls._instance is None:
            cls._instance = super(ActiveContext, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, max_size: int = 100):
        # Only initialize once
        if not self._initialized:
            self.max_size = max_size
            self.nodes: OrderedDict[str, Optional[Node]] = OrderedDict()
            self._context_path: Path = get_context_path()
            self._loaded_uris: set[str] = set()
            # Set of URIs that are protected from removal
            self._protected_uris: set[str] = set()
            self._load()
            ActiveContext._initialized = True

    @classmethod
    def get_instance(cls, max_size: int = 100) -> 'ActiveContext':
        """Get the singleton instance of ActiveContext."""
        if cls._instance is None:
            cls._instance = ActiveContext(max_size)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
        cls._initialized = False

    def _load(self):
        """Load context from file, including protected URIs."""
        if self._context_path.exists():
            try:
                with open(self._context_path, "r") as f:
                    data = json.load(f)
                    
                # Handle both old format (list) and new format (dict)
                if isinstance(data, list):
                    # Old format - just node URIs
                    node_uris = data
                    protected_uris = set()
                elif isinstance(data, dict):
                    # New format - has nodes and protected_uris
                    node_uris = data.get("nodes", [])
                    protected_uris = set(data.get("protected_uris", []))
                else:
                    return
                    
                # Initialize protected URIs
                self._protected_uris = protected_uris
                
                # Initialize nodes dict with None values (lazy loading)
                for uri in node_uris:
                    self.nodes[uri] = None
                    
            except (json.JSONDecodeError, KeyError):
                # If there's an error loading, start fresh
                pass

    def _save(self):
        self._context_path.parent.mkdir(parents=True, exist_ok=True)
        context_data = {
            "nodes": list(self.nodes.keys()),
            "protected_uris": list(self._protected_uris)
        }
        with open(self._context_path, "w") as f:
            json.dump(context_data, f)

    def add_protected_uri(self, uri: str):
        """Add a URI to the protected set, preventing it from being removed from context."""
        self._protected_uris.add(uri)
        self._save()

    def remove_protected_uri(self, uri: str):
        """Remove a URI from the protected set."""
        self._protected_uris.discard(uri)
        self._save()

    def is_protected(self, uri: str) -> bool:
        """Check if a URI is protected from removal."""
        return uri in self._protected_uris

    def get_protected_uris(self) -> set[str]:
        """Get the set of protected URIs."""
        return self._protected_uris.copy()

    def add(self, node: Node, protected: bool = False):
        """Add a node to the active context, optionally marking it as protected."""
        if protected:
            self.add_protected_uri(node.uri)
            
        if node.uri in self.nodes:
            self.nodes.move_to_end(node.uri)
        else:
            # Only remove nodes if we're at capacity and need to make space
            if len(self.nodes) >= self.max_size:
                # Find non-protected nodes to remove
                nodes_to_remove = []
                for uri in list(self.nodes.keys()):
                    if not self.is_protected(uri):
                        nodes_to_remove.append(uri)
                        if len(nodes_to_remove) >= (len(self.nodes) - self.max_size + 1):
                            break
                
                # Remove the oldest non-protected nodes
                for uri in nodes_to_remove:
                    self.nodes.pop(uri, None)
                
                # If we still don't have space, we need to increase capacity or reject
                if len(self.nodes) >= self.max_size:
                    # Log a warning but add anyway since it's protected
                    if protected:
                        # For protected nodes, we allow exceeding max_size
                        pass
                    else:
                        # For non-protected nodes, we can reject if no space
                        return
            
            self.nodes[node.uri] = node
        self._save()

    def get(self, uri: str, kg: KnowledgeGraph) -> Node | None:
        if uri in self.nodes and self.nodes[uri] is not None:
            self.nodes.move_to_end(uri)
            self._save()
            return self.nodes[uri]
        
        node = kg.get_node(uri)
        if node:
            self.add(node)
        return node

    def clear(self):
        """Clear the context but preserve protected nodes."""
        # Keep only protected nodes
        protected_nodes = {uri: node for uri, node in self.nodes.items() 
                         if self.is_protected(uri)}
        self.nodes.clear()
        self.nodes.update(protected_nodes)
        self._loaded_uris.clear()
        self._save()

    def force_clear(self):
        """Completely clear the context, including protected nodes."""
        self.nodes.clear()
        self._loaded_uris.clear()
        self._protected_uris.clear()
        self._save()
    
    def initialize_with_root_nodes(self, kg: KnowledgeGraph, workspace):
        """Initialize the active context with root nodes and project details for the workspace."""
        self.force_clear()  # Start completely fresh
        
        # Define root node URIs with expanded project details
        root_uris = [
            "dir://.",  # Root directory
            f"concept://{workspace.id}/project",  # Main project concept
            f"concept://{workspace.id}/project/structure",  # Project structure
            f"concept://{workspace.id}/project/goals",  # Project goals
            f"concept://{workspace.id}/project/architecture",  # Project architecture
            f"concept://{workspace.id}/project/configuration",  # Project configuration
        ]
        
        # Create project details nodes if they don't exist
        self._ensure_project_details_exist(kg, workspace)
        
        # Add root nodes to context as protected
        for uri in root_uris:
            node = kg.get_node(uri)
            if node:
                self.add(node, protected=True)
                
        # Also ensure key directories are added as protected
        key_directories = [
            "dir://src",
            "dir://design_docs",
        ]
        
        for dir_uri in key_directories:
            node = kg.get_node(dir_uri)
            if node:
                self.add(node, protected=True)

    def _ensure_project_details_exist(self, kg: KnowledgeGraph, workspace):
        """Ensure that project detail concepts exist in the knowledge graph."""
        project_details = {
            f"concept://{workspace.id}/project/structure": {
                "name": f"{workspace.id} - Project Structure",
                "content": "Core project structure and organization including source code layout, configuration files, and documentation structure."
            },
            f"concept://{workspace.id}/project/goals": {
                "name": f"{workspace.id} - Project Goals", 
                "content": "High-level goals and objectives of the project, including target functionality and success criteria."
            },
            f"concept://{workspace.id}/project/architecture": {
                "name": f"{workspace.id} - Architecture",
                "content": "System architecture, design patterns, and technical decisions governing the project implementation."
            },
            f"concept://{workspace.id}/project/configuration": {
                "name": f"{workspace.id} - Configuration",
                "content": f"Project configuration including workspace settings from {workspace.config.config_path.name} and build configuration."
            }
        }
        
        # Create concept nodes if they don't exist
        for uri, details in project_details.items():
            existing_node = kg.get_node(uri)
            if not existing_node:
                # Create the concept node
                from .models import Node
                node = Node(
                    uri=uri,
                    node_type="concept",
                    name=details["name"],
                    content=details["content"],
                    metadata={"auto_generated": True, "project_detail": True}
                )
                kg.add_node(node)
        
        # Ensure main project concept exists
        main_project_uri = f"concept://{workspace.id}/project"
        main_project_node = kg.get_node(main_project_uri)
        if not main_project_node:
            from .models import Node
            main_project_node = Node(
                uri=main_project_uri,
                node_type="concept",
                name=f"{workspace.id} - Main Project",
                content=f"Main project concept for {workspace.id} workspace, containing all project-related information and organization.",
                metadata={"auto_generated": True, "project_root": True}
            )
            kg.add_node(main_project_node)
        
        # Create relationships between project concepts
        self._create_project_concept_links(kg, workspace)

    def _create_project_concept_links(self, kg: KnowledgeGraph, workspace):
        """Create relationships between project concepts and directories."""
        from .models import Relation
        
        main_project_uri = f"concept://{workspace.id}/project"
        
        # Link main project to its sub-concepts
        sub_concepts = [
            f"concept://{workspace.id}/project/structure",
            f"concept://{workspace.id}/project/goals", 
            f"concept://{workspace.id}/project/architecture",
            f"concept://{workspace.id}/project/configuration"
        ]
        
        for sub_concept_uri in sub_concepts:
            # Create "contains" relationship from main project to sub-concepts
            contains_relation = Relation(
                id=None,
                source_uri=main_project_uri,
                target_uri=sub_concept_uri,
                relation_type="contains",
                weight=0.1,  # Low cost for easy traversal
                metadata={"auto_generated": True}
            )
            kg.add_relation(contains_relation)
            
            # Create "part_of" relationship from sub-concepts to main project
            part_of_relation = Relation(
                id=None,
                source_uri=sub_concept_uri,
                target_uri=main_project_uri,
                relation_type="part_of",
                weight=0.1,
                metadata={"auto_generated": True}
            )
            kg.add_relation(part_of_relation)
        
        # Link project concepts to relevant directories
        concept_directory_links = {
            f"concept://{workspace.id}/project/structure": ["dir://.", "dir://src", "dir://design_docs"],
            f"concept://{workspace.id}/project/goals": ["dir://design_docs"],
            f"concept://{workspace.id}/project/architecture": ["dir://src", "dir://design_docs"],
            f"concept://{workspace.id}/project/configuration": ["dir://."]
        }
        
        for concept_uri, dir_uris in concept_directory_links.items():
            for dir_uri in dir_uris:
                if kg.get_node(dir_uri):  # Only link if directory exists
                    # Create "describes" relationship from concept to directory
                    describes_relation = Relation(
                        id=None,
                        source_uri=concept_uri,
                        target_uri=dir_uri,
                        relation_type="describes",
                        weight=0.2,
                        metadata={"auto_generated": True}
                    )
                    kg.add_relation(describes_relation)
                    
                    # Create "described_by" relationship from directory to concept
                    described_by_relation = Relation(
                        id=None,
                        source_uri=dir_uri,
                        target_uri=concept_uri,
                        relation_type="described_by",
                        weight=0.2,
                        metadata={"auto_generated": True}
                    )
                    kg.add_relation(described_by_relation)
        
        # Link main project to root directory
        if kg.get_node("dir://."):
            located_in_relation = Relation(
                id=None,
                source_uri=main_project_uri,
                target_uri="dir://.",
                relation_type="located_in",
                weight=0.1,
                metadata={"auto_generated": True}
            )
            kg.add_relation(located_in_relation)
            
            contains_project_relation = Relation(
                id=None,
                source_uri="dir://.",
                target_uri=main_project_uri,
                relation_type="contains_project",
                weight=0.1,
                metadata={"auto_generated": True}
            )
            kg.add_relation(contains_project_relation)

    def list_nodes(self, kg: Optional[KnowledgeGraph] = None) -> list[Node]:
        result = []
        for uri, node in self.nodes.items():
            if node is not None:
                result.append(node)
            elif kg is not None:
                # Load the node if we have a knowledge graph
                loaded_node = kg.get_node(uri)
                if loaded_node:
                    self.nodes[uri] = loaded_node
                    result.append(loaded_node)
        return result

    def traverse(self, start_uri: str, kg: KnowledgeGraph, max_cost: float = 1.0) -> list[Node]:
        if not kg.get_node(start_uri):
            return []

        queue = deque([(start_uri, 0.0)])
        visited_costs = {start_uri: 0.0}
        
        context_nodes = []

        while queue:
            current_uri, current_cost = queue.popleft()
            
            node = self.get(current_uri, kg)
            if node:
                if node not in context_nodes:
                    context_nodes.append(node)

            relations = kg.get_relations(source_uri=current_uri)
            relations.extend(kg.get_relations(target_uri=current_uri))

            for relation in relations:
                if relation.source_uri == current_uri:
                    neighbor_uri = relation.target_uri
                else:
                    neighbor_uri = relation.source_uri

                new_cost = current_cost + relation.weight
                if new_cost <= max_cost:
                    if (
                        neighbor_uri not in visited_costs
                        or new_cost < visited_costs[neighbor_uri]
                    ):
                        visited_costs[neighbor_uri] = new_cost
                        queue.append((neighbor_uri, new_cost))
        
        return context_nodes 