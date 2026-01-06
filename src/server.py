#!/usr/bin/env python3
import os
from fastmcp import FastMCP
from tools import register_weather, register_ns, register_airlabs, register_obsidian

# Initialize the MCP Server
mcp = FastMCP("poke-mcp-server")

# Register all tools
register_weather(mcp)
register_ns(mcp)
register_airlabs(mcp)
register_obsidian(mcp)

@mcp.tool(description="Greet a user by name")
def greet(name: str) -> str:
    return f"Hello, {name}! Welcome to the Mega MCP server!"

@mcp.tool(description="Get server status")
def get_server_info() -> dict:
    return {
        "server_name": "Poke Custom MCP",
        "version": "1.2.0",
        "status": "online",
        "modules": ["Weather", "NS", "AirLabs", "Obsidian"]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"Starting FastMCP server on {host}:{port}")
    
    mcp.run(
        transport="http",
        host=host,
        port=port,
        stateless_http=True
    )