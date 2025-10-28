# MCP Integration Quick Start

## Installation

```bash
pip install langchain-mcp-adapters
```

## 30-Second Setup

```python
from elysia import Tree
from elysia.tools.additional import MCPServerAdapter

# 1. Create tree
tree = Tree()

# 2. Point to your MCP server script
adapter = MCPServerAdapter(server_script_path="/path/to/your/mcp_server.py")

# 3. Register all tools
await adapter.initialize_and_register_tools(tree, branch_id="base")

# 4. Use it!
response, objects = tree("Your query here")
```

## Common Use Cases

### 1. Basic: Register All Tools

```python
adapter = MCPServerAdapter(server_script_path="/path/to/server.py")
success, tools = await adapter.initialize_and_register_tools(tree)
print(f"Registered: {tools}")
```

### 2. Selective Registration

```python
adapter = MCPServerAdapter(server_script_path="/path/to/server.py")
await adapter.initialize()

# Choose specific tools
for tool in adapter.discovered_tools:
    if "search" in tool.name:
        tree.add_tool(tool, branch_id="base")
```

### 3. Multiple Servers

```python
servers = [
    "/path/to/server1.py",
    "/path/to/server2.py",
]

for server_path in servers:
    adapter = MCPServerAdapter(server_script_path=server_path)
    await adapter.initialize_and_register_tools(tree)
```

## How It Works

```
Your MCP Server Script
        ↓
langchain-mcp-adapters loads tools
        ↓
MCPServerAdapter wraps them as Elysia Tools
        ↓
Register with Elysia Tree
        ↓
Use like any other Elysia tool
```

## Example MCP Server Script

Create a simple MCP server (e.g., `my_server.py`):

```python
# This is just an example - implement your actual MCP server here
# See MCP documentation for server implementation details
```

## Testing

```python
adapter = MCPServerAdapter(server_script_path="/path/to/server.py")
success = await adapter.initialize()

if success:
    print(f"✓ Loaded {len(adapter.discovered_tools)} tools")
else:
    print("✗ Failed to load tools")
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Import error | `pip install langchain-mcp-adapters` |
| Server not found | Check server_script_path is correct |
| No tools loaded | Verify MCP server implements tools correctly |

## Next Steps

1. Create or locate your MCP server script
2. Run the example: `python examples/mcp_integration_example.py`
3. Integrate with your tree
4. Start using MCP tools!

---

**Simple. Minimal. No overengineering.** 🚀
