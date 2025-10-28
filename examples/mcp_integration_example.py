"""
Example: Using MCP Server Tools with Elysia

Demonstrates how to connect to an MCP server and use its tools within an Elysia Tree.
Requires: pip install langchain-mcp-adapters
"""
import asyncio
from elysia import Tree
from elysia.tools.additional import MCPServerAdapter


async def example_basic_usage():
    """Basic example: Connect to an MCP server and register all tools."""
    print("=== Basic MCP Integration Example ===\n")
    
    # Create Elysia tree
    tree = Tree(branch_initialisation="empty")
    
    # Create MCP adapter - point to your MCP server script
    # Replace with your actual MCP server path
    adapter = MCPServerAdapter(
        server_script_path="/path/to/your/mcp_server.py"
    )
    
    # Initialize and register all tools from the server
    print("Loading tools from MCP server...")
    success, registered_tools = await adapter.initialize_and_register_tools(
        tree=tree,
        branch_id="base"
    )
    
    if success:
        print(f"✓ Successfully registered {len(registered_tools)} tools:")
        for tool_name in registered_tools:
            print(f"  - {tool_name}")
    else:
        print("✗ Failed to connect to MCP server")
        return
    
    print("\nTree is ready! You can now run queries that use MCP tools.")


async def example_selective_registration():
    """Advanced example: Discover tools and selectively register them."""
    print("\n=== Selective Tool Registration Example ===\n")
    
    adapter = MCPServerAdapter(server_script_path="/path/to/your/mcp_server.py")
    
    # Initialize to discover tools
    print("Discovering tools from MCP server...")
    await adapter.initialize()
    
    # List all discovered tools
    print(f"\nDiscovered {len(adapter.discovered_tools)} tools:")
    for i, tool in enumerate(adapter.discovered_tools, 1):
        print(f"{i}. {tool.name}: {tool.description[:80]}...")
    
    # Create tree and selectively register tools
    tree = Tree(branch_initialisation="empty")
    
    # Example: Only register specific tools
    for tool in adapter.discovered_tools:
        if "search" in tool.name.lower():
            tree.add_tool(tool, branch_id="base")
            print(f"\n✓ Registered: {tool.name}")


async def example_multiple_servers():
    """Example: Connect to multiple MCP servers."""
    print("\n=== Multiple MCP Servers Example ===\n")
    
    tree = Tree(branch_initialisation="empty")
    
    # Configure multiple MCP server scripts
    servers = [
        {
            "path": "/path/to/server1.py",
            "name": "Local Tools",
            "branch": "local_tools"
        },
        {
            "path": "/path/to/server2.py",
            "name": "API Tools",
            "branch": "api_tools"
        },
    ]
    
    for server_config in servers:
        print(f"\nConnecting to {server_config['name']}...")
        
        adapter = MCPServerAdapter(server_script_path=server_config["path"])
        
        success, registered = await adapter.initialize_and_register_tools(
            tree=tree,
            branch_id=server_config["branch"]
        )
        
        if success:
            print(f"✓ Registered {len(registered)} tools from {server_config['name']}")
        else:
            print(f"✗ Failed to connect to {server_config['name']}")


async def main():
    """Run all examples."""
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║       MCP Server Integration Examples for Elysia         ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")
    
    print("Requirements:")
    print("  pip install langchain-mcp-adapters\n")
    print("Note: Update the server_script_path to point to your MCP server.\n")
    
    try:
        await example_basic_usage()
    except Exception as e:
        print(f"Basic usage example error: {e}")
    
    try:
        await example_selective_registration()
    except Exception as e:
        print(f"Selective registration example error: {e}")
    
    try:
        await example_multiple_servers()
    except Exception as e:
        print(f"Multiple servers example error: {e}")
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
