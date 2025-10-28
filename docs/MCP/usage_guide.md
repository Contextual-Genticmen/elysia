# MCP Tools Usage Guide

## Overview

MCP (Model Context Protocol) tools are automatically loaded and made available to all Elysia Trees when configured in `elysia/mcp.json`.

## Configuration

### Location
- **File**: `elysia/mcp.json` (at Elysia module root)
- **Format**: JSON configuration file

### Example Configuration

```json
{
  "servers": [
    {
      "name": "example_server",
      "description": "Example MCP server providing search tools",
      "server_script_path": "/path/to/mcp_server.py",
      "enabled": true
    },
    {
      "name": "another_server",
      "description": "Another MCP server",
      "server_script_path": "/path/to/another_server.py",
      "enabled": false
    }
  ]
}
```

### Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier for the MCP server |
| `description` | No | Human-readable description |
| `server_script_path` | Yes | Path to the MCP server Python script |
| `enabled` | Yes | Whether to load this server (true/false) |

## How It Works

### 1. At Application Startup

```
Application Start
    ↓
Import custom_tools
    ↓
Import mcp_loader
    ↓
load_mcp_servers_from_config()
    ↓
Read elysia/mcp.json
    ↓
For each enabled server:
    - Connect to MCP server via langchain-mcp-adapters
    - Create MCPTool subclass: MCP_{server_name}
    - Inject into custom_tools namespace
    ↓
Tools available via /tools/available API
```

### 2. Dynamic Tool Class Creation

For a server named `"example_server"`, a class `MCP_example_server` is created:

```python
class MCP_example_server(MCPTool):
    """Dynamically created MCP server tool."""
    
    def __init__(self, **kwargs):
        super().__init__(
            server_name="example_server",
            server_script_path="/path/to/mcp_server.py",
            **kwargs,
        )
```

### 3. Tool Discovery

The tool is automatically discovered by:

```python
# In util/tool_discovery.py (called by routes/tools.py)
def discover_tools_from_module():
    # Inspects custom_tools module
    # Finds MCP_example_server class
    # Returns tool class dict

def get_tool_metadata():
    # Gets metadata from discovered tools
    # Returns metadata for API
```

### 4. Using MCP Tools

#### Option A: Automatic (Recommended)

MCP tools are automatically available to all Trees created via the API:

```bash
# 1. Initialize user
curl -X POST http://localhost:8000/init/user/my_user

# 2. Initialize tree
curl -X POST http://localhost:8000/init/tree/my_user/my_conversation \
  -H "Content-Type: application/json" -d '{"low_memory": false}'

# 3. MCP tool is available in the tree!
# Use it by name in queries to the tree
```

#### Option B: Programmatic

Add MCP tool to a specific Tree:

```python
from elysia.tree.tree import Tree
from elysia.api.custom_tools import MCP_example_server

# Create tree
tree = Tree()

# Add MCP tool to a branch
mcp_tool = MCP_example_server()
tree.add_tool(mcp_tool, branch_id="base")

# Now the tree can use the MCP server's tools
```

## MCP Tool Capabilities

Each MCP tool (e.g., `MCP_example_server`) provides:

### Actions

1. **List Tools** - See what tools the MCP server provides
   ```python
   inputs = {"action": "list"}
   # Returns list of available tools from the server
   ```

2. **Execute Tool** - Run a specific tool from the server
   ```python
   inputs = {
       "action": "execute",
       "tool_name": "search",
       "tool_inputs": {"query": "machine learning"}
   }
   # Executes the 'search' tool on the MCP server
   ```

### Metadata

Each MCP tool has metadata accessible via `/tools/available`:

```json
{
  "MCP_example_server": {
    "name": "mcp_example_server",
    "description": "MCP server 'example_server' - provides access to multiple tools via Model Context Protocol",
    "inputs": {
      "action": {
        "description": "Action: 'list' to show tools, 'execute' to run a specific tool",
        "type": "str",
        "default": "list"
      },
      "tool_name": {
        "description": "Name of the tool to execute (required when action='execute')",
        "type": "str",
        "required": false
      },
      "tool_inputs": {
        "description": "Inputs for the tool (required when action='execute')",
        "type": "dict",
        "required": false,
        "default": {}
      }
    }
  }
}
```

## Example Workflow

### Step 1: Create MCP Server Script

```python
# my_mcp_server.py
# Implement your MCP server following MCP protocol
# See: https://github.com/modelcontextprotocol/
```

### Step 2: Configure in mcp.json

```json
{
  "servers": [
    {
      "name": "my_search_server",
      "description": "Custom search server",
      "server_script_path": "/app/my_mcp_server.py",
      "enabled": true
    }
  ]
}
```

### Step 3: Rebuild Container

```bash
docker-compose build elysia
docker-compose up -d elysia
```

### Step 4: Verify Tool is Available

```bash
curl http://localhost:8000/tools/available | jq '.tools | keys'
# Should include "MCP_my_search_server"
```

### Step 5: Use in Tree

The tool is automatically available to all Trees. The AI can decide to use it based on:
- Tool name: `mcp_my_search_server`
- Tool description
- Available actions (list, execute)

## Architecture Benefits

### 1. Zero Code Changes Required

Once configured in `mcp.json`, MCP tools are automatically:
- Loaded at startup
- Discovered by the API
- Available to all Trees

### 2. Consistent Interface

All MCP tools follow the same interface:
- Standard inputs (action, tool_name, tool_inputs)
- Standard outputs (Status, Result, Error, Text)
- Elysia Tool compatibility

### 3. Dynamic Loading

- Add/remove MCP servers without changing code
- Enable/disable servers with a config flag
- Hot-reload by rebuilding container

### 4. Isolation

Each MCP server runs in isolation:
- Separate process
- Clear boundaries
- No cross-contamination

## Troubleshooting

### Tool Not Appearing

1. Check `mcp.json` syntax is valid JSON
2. Ensure `enabled: true` for the server
3. Verify `server_script_path` is correct
4. Rebuild container: `docker-compose build elysia`
5. Check logs: `docker-compose logs elysia | grep -i mcp`

### Tool Execution Fails

1. Verify MCP server script is valid
2. Check tool inputs match MCP server expectations
3. Review error messages in tree execution
4. Test MCP server independently

### Import Errors

If you see errors about `langchain-mcp-adapters`:

```bash
# In Dockerfile or requirements, ensure:
pip install langchain-mcp-adapters
```

## Current Status

### Installed
- ✅ MCP integration framework
- ✅ Tool discovery mechanism
- ✅ API endpoints
- ✅ Configuration file (`mcp.json`)
- ✅ Dynamic class creation
- ✅ Automatic registration

### Configuration
- **Location**: `elysia/mcp.json`
- **Current State**: Empty (no servers enabled)
- **Status**: Ready for configuration

### To Enable
1. Create or locate MCP server script
2. Add configuration to `mcp.json`
3. Set `enabled: true`
4. Rebuild container
5. Tools automatically available!

## Reference

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/tools/available` | GET | List all available tools (including MCP) |
| `/init/user/{user_id}` | POST | Initialize user with TreeManager |
| `/init/tree/{user_id}/{conversation_id}` | POST | Initialize Tree with default tools |

### File Locations

| Path | Purpose |
|------|---------|
| `elysia/mcp.json` | MCP server configuration |
| `elysia/mcp.example.json` | Example configuration |
| `elysia/tools/mcp/mcp_tool.py` | MCPTool base class |
| `elysia/tools/mcp/mcp_loader.py` | Dynamic tool loader |
| `elysia/api/custom_tools.py` | Tool registration |

### Related Documentation

- `ARCHITECTURE.md` - Technical architecture details
- `QUICKSTART.md` - Quick setup guide  
- `INTEGRATION_SUMMARY.md` - API flow documentation
- `SUMMARY.md` - High-level overview

---

**MCP tools are ready to use! Configure `mcp.json` and rebuild to enable.** 🚀

