#!/usr/bin/env python3
"""
Knowledge Engine MCP Server using FastMCP decorator pattern.

This module provides a Model Context Protocol (MCP) server implementation for the Knowledge Engine.
It exposes various tools for managing concepts, relations, resources, and active context through
a standardized MCP interface.

The server uses the FastMCP framework to provide the following capabilities:
- Concept management (create, read, update, delete, move)
- Relationship management (create, delete, query)
- Resource management (delete)
- Knowledge graph traversal
- Active context management
- Workspace bootstrapping

Key Features:
- Automatic markdown link parsing for concept relationships
- Protected concept URIs in active context
- Comprehensive error handling and logging
- Singleton pattern for active context management
- Database connection management

Usage:
    This server is typically started via the CLI or through the start_server.py script.
    It communicates using JSON-RPC over stdio following the MCP specification.
"""
import logging
import sys
from pathlib import Path
import toml

from fastmcp import FastMCP

from ..core.active_context import ActiveContext
from ..core.knowledge_graph import KnowledgeGraph
from ..tools import concepts, relations, resources, traverse, context
from ..tools.resources import bootstrap as bootstrap_tool

# Set up logging to stderr to avoid interfering with MCP JSON-RPC on stdout
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_mcp_server(workspace_root=None, workspace_id=None, db_path=None) -> FastMCP:
    """
    Create and configure the MCP server with all knowledge engine tools.
    
    This function initializes a FastMCP server instance and registers all the knowledge engine
    tools as MCP tools. It handles workspace configuration, database connection setup, and
    provides comprehensive error handling.
    
    Args:
        workspace_root (Path, optional): Path to the workspace root directory. Used for
            configuration and relative path resolution.
        workspace_id (str, optional): Unique identifier for the workspace. Used in logging
            and concept URI generation.
        db_path (Path, optional): Path to the SQLite database file. Required for all
            knowledge graph operations.
    
    Returns:
        FastMCP: Configured MCP server instance with all tools registered.
        
    Raises:
        ValueError: If required parameters (especially db_path) are missing.
        Exception: If database connection fails or server initialization fails.
        
    Example:
        >>> server = create_mcp_server(
        ...     workspace_root=Path("/path/to/workspace"),
        ...     workspace_id="my_project",
        ...     db_path=Path("/path/to/knowledge.db")
        ... )
    """
    
    try:
        # Create MCP server
        mcp = FastMCP("knowledge-engine")
        
        # Log initialization (following MCP debugging guidelines)
        logging.info(f"Initializing MCP server for workspace: {workspace_id}")
        logging.info(f"Database path: {db_path}")
        
        # Test database connection early
        if db_path is None:
            raise ValueError("Database path is required")
        test_kg = KnowledgeGraph(db_path=db_path)
        node_count = test_kg.get_node_count()
        logging.info(f"Database connection verified: {node_count} nodes")
        
    except Exception as e:
        logging.error(f"Failed to initialize MCP server: {e}")
        raise
    
    @mcp.tool
    def test_connection() -> str:
        """
        Test MCP server connection and return server status.
        
        This tool provides a simple way to verify that the MCP server is running correctly
        and can access the knowledge graph database. It returns basic statistics about
        the current workspace.
        
        Returns:
            str: Status message containing workspace ID, node count, and relation count.
                Format: "MCP server connected. Workspace: {id}, Nodes: {count}, Relations: {count}"
                
        Example:
            >>> test_connection()
            "MCP server connected. Workspace: knowledge_engine, Nodes: 42, Relations: 15"
        """
        try:
            logging.info("MCP test_connection tool called")
            kg = create_kg()
            node_count = kg.get_node_count()
            relation_count = kg.get_relation_count()
            return f"MCP server connected. Workspace: {workspace_id}, Nodes: {node_count}, Relations: {relation_count}"
        except Exception as e:
            logging.error(f"MCP test_connection failed: {e}")
            return f"Error: {e}"
    
    def create_kg():
        """
        Create a new knowledge graph instance.
        
        This internal helper function creates a KnowledgeGraph instance using the configured
        database path. It includes error handling and logging for debugging purposes.
        
        Returns:
            KnowledgeGraph: A new knowledge graph instance connected to the workspace database.
            
        Raises:
            ValueError: If the workspace/database path is not initialized.
            Exception: If database connection or initialization fails.
        """
        if db_path is None:
            raise ValueError("Workspace not initialized")
        try:
            kg = KnowledgeGraph(db_path=db_path)
            logging.debug("Knowledge graph instance created successfully")
            return kg
        except Exception as e:
            logging.error(f"Failed to create knowledge graph: {e}")
            raise

    def get_active_context():
        """
        Get the singleton active context instance.
        
        This internal helper function retrieves the singleton ActiveContext instance,
        which manages the current working set of nodes in memory. The active context
        provides fast access to recently used or important concepts.
        
        Returns:
            ActiveContext: The singleton active context instance.
            
        Raises:
            Exception: If the active context cannot be retrieved or initialized.
        """
        try:
            ac = ActiveContext.get_instance()
            logging.debug("Active context instance retrieved")
            return ac
        except Exception as e:
            logging.error(f"Failed to get active context: {e}")
            raise

    # Tool definitions using decorators
    @mcp.tool
    def bootstrap_command() -> str:
        """
        Bootstrap the knowledge graph from the current workspace.
        
        This tool scans the workspace directory structure and creates nodes for all
        directories and files, establishing the foundational knowledge graph structure.
        It's typically run once when setting up a new workspace.
        
        The bootstrap process:
        1. Scans the workspace directory recursively
        2. Creates directory nodes for each folder
        3. Creates resource nodes for each file
        4. Establishes containment relationships
        5. Initializes the active context with root nodes
        
        Returns:
            str: Success message indicating bootstrap completion.
            
        Example:
            >>> bootstrap_command()
            "Bootstrap completed"
        """
        try:
            logging.info("MCP bootstrap_command tool called")
            kg = create_kg()
            result = bootstrap_tool(kg)
            logging.info("Bootstrap completed successfully")
            return str(result) if result is not None else "Bootstrap completed"
        except Exception as e:
            logging.error(f"Bootstrap failed: {e}")
            return f"Error: {e}"

    @mcp.tool
    def add_concept(uri: str, name: str, content: str) -> str:
        """
        Add a new concept to the knowledge graph.
        
        Creates a new concept node with the specified URI, name, and content. The content
        is automatically parsed for markdown links to other concepts, and 'references'
        relationships are created automatically.
        
        Args:
            uri (str): Unique identifier for the concept (e.g., "concept://project/goals").
            name (str): Human-readable name for the concept.
            content (str): Detailed content/description. Supports markdown with automatic
                linking to other concepts using [text](concept://uri) syntax.
        
        Returns:
            str: Success message with the concept name and URI.
            
        Example:
            >>> add_concept(
            ...     "concept://project/architecture", 
            ...     "System Architecture",
            ...     "The system follows a modular architecture with [clear separation](concept://project/principles)."
            ... )
            "Added concept: System Architecture (concept://project/architecture)"
        """
        try:
            kg = create_kg()
            result = concepts.add_concept(kg, uri, name, content)
            return f"Added concept: {result.name} ({result.uri})"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def get_concept(uri: str) -> str:
        """
        Get a concept from the knowledge graph.
        
        Retrieves a concept by its URI and returns its details including name, URI,
        and content. If the concept doesn't exist, returns an appropriate message.
        
        Args:
            uri (str): The unique identifier of the concept to retrieve.
        
        Returns:
            str: Formatted concept details or "No concept found" message.
            
        Example:
            >>> get_concept("concept://project/goals")
            "Concept: Project Goals
            URI: concept://project/goals
            Content: The main objectives of this project..."
        """
        try:
            kg = create_kg()
            result = concepts.get_concept(kg, uri)
            if result:
                return f"Concept: {result.name}\nURI: {result.uri}\nContent: {result.content}"
            return f"No concept found with URI: {uri}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def update_concept(uri: str, name: str, content: str) -> str:
        """
        Update an existing concept in the knowledge graph.
        
        Updates the name and content of an existing concept. The content is automatically
        parsed for markdown links, and concept relationships are updated accordingly.
        Old auto-generated relationships are removed and new ones are created.
        
        Args:
            uri (str): The unique identifier of the concept to update.
            name (str): New name for the concept.
            content (str): New content/description. Supports markdown with automatic
                linking to other concepts.
        
        Returns:
            str: Success message with the updated concept name and URI, or error message
                if the concept doesn't exist.
                
        Example:
            >>> update_concept(
            ...     "concept://project/goals",
            ...     "Updated Project Goals", 
            ...     "Revised objectives including [new requirements](concept://project/requirements)."
            ... )
            "Updated concept: Updated Project Goals (concept://project/goals)"
        """
        try:
            kg = create_kg()
            result = concepts.update_concept(kg, uri, name, content)
            if result:
                return f"Updated concept: {result.name} ({result.uri})"
            return f"No concept found with URI: {uri}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def delete_concept(uri: str) -> str:
        """
        Delete a concept from the knowledge graph.
        
        Permanently removes a concept and all its associated relationships from the
        knowledge graph. This operation cannot be undone.
        
        Args:
            uri (str): The unique identifier of the concept to delete.
        
        Returns:
            str: Success or failure message indicating the result of the deletion.
            
        Warning:
            This operation is permanent and will remove all relationships involving
            this concept. Consider the impact on related concepts before deletion.
            
        Example:
            >>> delete_concept("concept://project/deprecated_feature")
            "Concept deleted: True"
        """
        try:
            kg = create_kg()
            result = concepts.delete_concept(kg, uri)
            return f"Concept deleted: {result}" if result else f"Failed to delete concept: {uri}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def move_concept(old_uri: str, new_uri: str) -> str:
        """
        Move a concept to a new URI.
        
        Changes the URI of an existing concept while preserving all its relationships
        and content. All relationships are automatically updated to point to the new URI.
        
        Args:
            old_uri (str): The current URI of the concept to move.
            new_uri (str): The new URI for the concept.
        
        Returns:
            str: Success message indicating the move result.
            
        Example:
            >>> move_concept(
            ...     "concept://project/old_name",
            ...     "concept://project/new_name"
            ... )
            "Concept moved from concept://project/old_name to concept://project/new_name: True"
        """
        try:
            kg = create_kg()
            result = concepts.move_concept(kg, old_uri, new_uri)
            return f"Concept moved from {old_uri} to {new_uri}: {result}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def delete_resource(uri: str) -> str:
        """
        Delete a resource from the knowledge graph.
        
        Permanently removes a resource node (typically representing a file) from the
        knowledge graph. This is different from delete_concept as it's specifically
        for resource nodes rather than concept nodes.
        
        Args:
            uri (str): The unique identifier of the resource to delete.
        
        Returns:
            str: Success or failure message indicating the result of the deletion.
            
        Example:
            >>> delete_resource("file://path/to/obsolete_file.txt")
            "Resource deleted: True"
        """
        try:
            kg = create_kg()
            result = resources.delete_resource(kg, uri)
            return f"Resource deleted: {result}" if result else f"Failed to delete resource: {uri}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def link_nodes(source_uri: str, target_uri: str, relation_type: str, weight: float = 1.0) -> str:
        """
        Link two nodes with a relation.
        
        Creates a directed relationship between two nodes in the knowledge graph.
        The relationship has a type and weight that affects graph traversal.
        
        Args:
            source_uri (str): URI of the source node.
            target_uri (str): URI of the target node.
            relation_type (str): Type of relationship (e.g., "contains", "references", "implements").
            weight (float, optional): Traversal weight/cost (0.0 to 1.0). Lower values indicate
                stronger relationships. Defaults to 1.0.
        
        Returns:
            str: Success message showing the created relationship.
            
        Example:
            >>> link_nodes(
            ...     "concept://project/goals",
            ...     "concept://project/requirements", 
            ...     "leads_to",
            ...     0.3
            ... )
            "Created relation: concept://project/goals --[leads_to]--> concept://project/requirements (weight: 0.3)"
        """
        try:
            kg = create_kg()
            result = relations.link_nodes(kg, source_uri, target_uri, relation_type, weight)
            return f"Created relation: {source_uri} --[{relation_type}]--> {target_uri} (weight: {weight})"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def unlink_nodes(source_uri: str, target_uri: str, relation_type: str) -> str:
        """
        Remove a relation between two nodes.
        
        Deletes a specific relationship between two nodes. Only the exact relationship
        matching the source, target, and type is removed.
        
        Args:
            source_uri (str): URI of the source node.
            target_uri (str): URI of the target node.
            relation_type (str): Type of relationship to remove.
        
        Returns:
            str: Success message confirming the relationship removal.
            
        Example:
            >>> unlink_nodes(
            ...     "concept://project/goals",
            ...     "concept://project/requirements",
            ...     "leads_to"
            ... )
            "Removed relation: concept://project/goals --[leads_to]--> concept://project/requirements"
        """
        try:
            kg = create_kg()
            relations.unlink_nodes(kg, source_uri, target_uri, relation_type)
            return f"Removed relation: {source_uri} --[{relation_type}]--> {target_uri}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def get_relations_for_node(uri: str) -> str:
        """
        Get all relations for a node.
        
        Retrieves all relationships (both incoming and outgoing) for a specific node.
        The results show the relationship type, connected node, and traversal weight.
        
        Args:
            uri (str): URI of the node to get relations for.
        
        Returns:
            str: Formatted list of all relationships for the node, or "No relations found" message.
            
        Example:
            >>> get_relations_for_node("concept://project/goals")
            "Relations for concept://project/goals:
              --[leads_to]--> concept://project/requirements (weight: 0.3)
              <--[part_of]-- concept://project (weight: 0.1)"
        """
        try:
            kg = create_kg()
            result = relations.get_relations_for_node(kg, uri)
            if not result:
                return f"No relations found for node: {uri}"
            
            relations_text = []
            for rel in result:
                if rel.source_uri == uri:
                    relations_text.append(f"  --[{rel.relation_type}]--> {rel.target_uri} (weight: {rel.weight})")
                else:
                    relations_text.append(f"  <--[{rel.relation_type}]-- {rel.source_uri} (weight: {rel.weight})")
            
            return f"Relations for {uri}:\n" + "\n".join(relations_text)
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def traverse_graph(start_uri: str, max_cost: float = 1.0) -> str:
        """
        Traverse the knowledge graph from a starting node.
        
        Performs a breadth-first traversal of the knowledge graph starting from the
        specified node, following relationships up to the maximum cost limit. The
        results are added to the active context for easy access.
        
        Args:
            start_uri (str): URI of the node to start traversal from.
            max_cost (float, optional): Maximum cumulative cost for traversal. Defaults to 1.0.
                Lower values limit traversal to closer/stronger relationships.
        
        Returns:
            str: Formatted list of nodes discovered during traversal, or "No nodes found" message.
            
        Example:
            >>> traverse_graph("concept://project/goals", 0.5)
            "Traversed from concept://project/goals (max_cost: 0.5):
              Project Requirements (concept://project/requirements)
              Main Project (concept://project)"
        """
        try:
            ac = get_active_context()
            kg = create_kg()
            result = ac.traverse(start_uri, kg, max_cost)
            if not result:
                return f"No nodes found during traversal from {start_uri}"
            
            nodes_text = []
            for node in result:
                nodes_text.append(f"  {node.name} ({node.uri})")
            
            return f"Traversed from {start_uri} (max_cost: {max_cost}):\n" + "\n".join(nodes_text)
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def get_active_context_tool() -> str:
        """
        Get the current active context.
        
        Returns all nodes currently in the active context, which represents the
        current working set of concepts and resources. The active context provides
        fast access to recently used or important nodes.
        
        Returns:
            str: Formatted list of nodes in the active context, or "Active context is empty" message.
            
        Example:
            >>> get_active_context_tool()
            "Active context contains 3 nodes:
              Project Goals (concept://project/goals)
              Main Project (concept://project)
              Root Directory (dir://.)"
        """
        try:
            ac = get_active_context()
            kg = create_kg()
            result = ac.list_nodes(kg)
            if not result:
                return "Active context is empty"
            
            context_text = []
            for node in result:
                context_text.append(f"  {node.name} ({node.uri})")
            
            return f"Active context contains {len(result)} nodes:\n" + "\n".join(context_text)
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def add_to_active_context(uri: str) -> str:
        """
        Add a node to the active context.
        
        Adds a specific node to the active context, making it easily accessible
        for future operations. The active context maintains a working set of
        frequently used nodes.
        
        Args:
            uri (str): URI of the node to add to the active context.
        
        Returns:
            str: Success message with the node name and URI, or "Node not found" message.
            
        Example:
            >>> add_to_active_context("concept://project/architecture")
            "Added to active context: System Architecture (concept://project/architecture)"
        """
        try:
            ac = get_active_context()
            kg = create_kg()
            node = kg.get_node(uri)
            if node:
                ac.add(node)
                return f"Added to active context: {node.name} ({uri})"
            return f"Node not found: {uri}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool
    def clear_active_context() -> str:
        """
        Clear the active context.
        
        Removes all nodes from the active context except for protected nodes.
        Protected nodes (such as project root concepts) are preserved to maintain
        essential workspace context.
        
        Returns:
            str: Success message confirming the context was cleared.
            
        Note:
            This operation preserves protected nodes like project concepts and
            key directories. Use force_clear if you need to remove everything.
            
        Example:
            >>> clear_active_context()
            "Active context cleared"
        """
        try:
            ac = get_active_context()
            ac.clear()
            return "Active context cleared"
        except Exception as e:
            return f"Error: {e}"

    # Resource definitions
    @mcp.resource("concept://{path*}")
    def get_concept_resource(path: str) -> str:
        """
        Get the LLM-digestible representation of a concept resource.
        
        Args:
            path (str): The path part of the concept URI, e.g., "project/goals".
            
        Returns:
            str: A formatted string containing the concept's name and content,
                 or an error message if not found.
        """
        uri = f"concept://{path}"
        logging.info(f"Received request for concept resource: {uri}")
        kg = create_kg()
        node = kg.get_node(uri)
        if node and node.node_type == "concept":
            return f"# Concept: {node.name}\\n\\n{node.content}"
        return f"Error: Concept not found at {uri}"

    @mcp.resource("file://{path*}")
    def get_file_resource(path: str) -> str:
        """
        Get the contents of a file resource.
        
        Args:
            path (str): The file path relative to the workspace root, e.g., "src/main.py".
            
        Returns:
            str: The content of the file, or an error message if not found.
        """
        uri = f"file://{path}"
        logging.info(f"Received request for file resource: {uri}")
            
        # This assumes workspace_root is available from the parent scope
        if workspace_root is None:
            return "Error: Workspace root not configured on the server."
            
        file_path = Path(workspace_root) / path
        
        if file_path.is_file():
            try:
                return file_path.read_text()
            except Exception as e:
                return f"Error reading file {file_path}: {e}"
        return f"Error: File not found at {file_path}"

    # Log successful server creation (following MCP debugging guidelines)
    logging.info("MCP server created successfully with all tools registered")
    logging.info("MCP server ready for connections")
    
    return mcp
