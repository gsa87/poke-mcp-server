#!/usr/bin/env python3
import os
import sys
from fastmcp import FastMCP
from tools import register_weather, register_ns, register_airlabs, register_obsidian

# Initialize the MCP Server
mcp = FastMCP("poke-mcp-server")

# Helper to register tools with logging
def register_module(name, register_func):
    print(f"--- Registering {name} module ---", file=sys.stderr)
    try:
        register_func(mcp)
        print(f"✅ {name} module registered successfully.", file=sys.stderr)
    except Exception as e:
        print(f"❌ Failed to register {name} module: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

# Register all tools
register_module("Weather", register_weather)
register_module("NS", register_ns)
register_module("AirLabs", register_airlabs)
register_module("Obsidian", register_obsidian)

@mcp.tool(description="Greet a user by name")
def greet(name: str) -> str:
    return f"Hello, {name}! Welcome to the Mega MCP server!"

@mcp.tool(description="Get server status")
def get_server_info() -> dict:
    return {
        "server_name": "Poke Custom MCP",
        "version": "1.3.0",
        "status": "online",
        "modules": ["Weather", "NS", "AirLabs", "Obsidian"]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"Starting FastMCP server on {host}:{port}", file=sys.stderr)
    
    mcp.run(
        transport="http",
        host=host,
        port=port,
        stateless_http=True
    )