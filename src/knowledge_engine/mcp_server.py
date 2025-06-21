#!/usr/bin/env python3
"""
Knowledge Engine MCP Server - Stdio Mode
"""

import logging
import sys
from fastmcp import FastMCP

# Setup logging to a file to debug Cursor connection issues
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log')
        # Do NOT log to stdout, as it's used for MCP communication
    ]
)
logger = logging.getLogger(__name__)

# Create MCP instance
mcp = FastMCP("knowledge-engine")

@mcp.tool()
async def hello_world() -> str:
    """A simple hello world tool."""
    logger.info("The hello_world tool was called successfully.")
    return "Hello World!"

def run_server():
    """Run the MCP server using stdio."""
    logger.info("Starting MCP server in stdio mode...")
    logger.info("Available tools: hello_world")
    logger.info("Waiting for a connection from the client (e.g., Cursor)...")
    try:
        mcp.run() # Defaults to stdio transport
    except Exception as e:
        logger.error(f"MCP server crashed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    run_server()