#!/usr/bin/env python3
"""
Knowledge Engine MCP Server

A minimal MCP server that provides basic tools for Claude Desktop integration.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeEngineServer:
    """Knowledge Engine MCP Server implementation."""
    
    def __init__(self):
        self.mcp = FastMCP("knowledge-engine")
        self._setup_tools()
    
    def _setup_tools(self):
        """Register all available tools."""
        
        async def hello_world_func() -> str:
            """
            A simple hello world tool that returns a greeting message.
            
            Returns:
                str: "Hello World!" message
            """
            logger.info("hello_world tool called")
            return "Hello World!"
        
        self.hello_world_func = hello_world_func
        self.hello_world = self.mcp.tool()(hello_world_func)
    
    async def start(self):
        """Start the MCP server."""
        logger.info("Starting Knowledge Engine MCP Server...")
        await self.mcp.run()


async def main():
    """Main entry point for the MCP server."""
    server = KnowledgeEngineServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main()) 