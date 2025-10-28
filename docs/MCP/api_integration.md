# MCP Integration Summary - API Flow

## Overview

MCP (Model Context Protocol) tools are now fully integrated into the Elysia API flow and can be automatically discovered and used by Trees.

## Architecture Flow

### 1. Application Startup (`app.py`)

```
app.py (FastAPI application)
    ↓
includes router: tools.router at /tools
    ↓
imports: elysia.api.custom_tools
```

### 2. Tool Discovery (`custom_tools.py`)

```python
# elysia/api/custom_tools.py
from elysia.tools.mcp import mcp_loader  # Triggers MCP tool loading

# Import dynamically created MCP tool classes
for _mcp_tool_name in mcp_loader.__all__:
    globals()[_mcp_tool_name] = getattr(mcp_loader, _mcp_tool_name)
```

**Key Points:**
- Importing `mcp_loader` triggers `load_mcp_servers_from_config()` at module import time
- Dynamically created MCP tool classes are injected into `custom_tools` module namespace
- `discover_tools_from_module()` in `util/tool_discovery.py` can discover them

### 3. MCP Tool Loading (`mcp_loader.py`)

```python
# elysia/tools/mcp/mcp_loader.py

def load_mcp_servers_from_config() -> list[type[MCPTool]]:
    """
    1. Reads elysia/mcp.json
    2. For each enabled server:
       - Creates a dynamic MCPTool subclass
       - Names it: MCP_{server_name}
    3. Returns list of tool classes
    """

# Executed at module import time
_loaded_tool_classes = load_mcp_servers_from_config()

# Export to module namespace
for tool_class in _loaded_tool_classes:
    globals()[tool_class.__name__] = tool_class
```

### 4. User Initialization Flow

```
POST /init/user/{user_id}
    ↓
UserManager.add_user_local(user_id, config)
    ↓
Creates TreeManager(user_id, config)
    ↓
TreeManager stores Config with Settings
```

### 5. Tree Initialization Flow

```
POST /init/tree/{user_id}/{conversation_id}
    ↓
UserManager.initialise_tree(user_id, conversation_id)
    ↓
TreeManager.add_tree(conversation_id)
    ↓
Creates Tree(settings=TreeManager.settings)
    ↓
Tree.__init__:
    - Initializes with default branch initialization
    - Loads default tools (Query, Aggregate, etc.)
    - Ready to accept additional tools
```

### 6. Tool Registration with Tree

MCP tools can be added to a Tree in two ways:

#### Option A: Programmatic (for custom scripts)
```python
from elysia.tools.mcp import MCPTool

tree = Tree()
mcp_tool = MCPTool(
    server_name="my_server",
    server_script_path="/path/to/server.py"
)
tree.add_tool(mcp_tool, branch_id="base")
```

#### Option B: Configuration-based (via mcp.json)
```json
{
  "servers": [
    {
      "name": "example_server",
      "description": "Example MCP server",
      "server_script_path": "/path/to/server.py",
      "enabled": true
    }
  ]
}
```

When enabled in `mcp.json`:
1. Tool class `MCP_example_server` is created automatically
2. Available via `/tools/available` API endpoint
3. Can be instantiated and added to any Tree

## Complete API Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Application Startup                                         │
├─────────────────────────────────────────────────────────────┤
│ 1. app.py starts FastAPI                                   │
│ 2. Imports custom_tools module                             │
│ 3. custom_tools imports mcp_loader                         │
│ 4. mcp_loader.load_mcp_servers_from_config() executes     │
│ 5. Reads elysia/mcp.json                                   │
│ 6. Creates MCPTool subclasses for enabled servers          │
│ 7. Injects classes into custom_tools namespace             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ User Initialization (POST /init/user/{user_id})           │
├─────────────────────────────────────────────────────────────┤
│ 1. UserManager.add_user_local(user_id)                    │
│ 2. Creates TreeManager(user_id, config=None)              │
│ 3. TreeManager initializes with default Config            │
│ 4. Config contains Settings (API keys, LLM settings)       │
│ 5. ClientManager created with Settings                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Tree Initialization (POST /init/tree/{user_id}/{conv_id}) │
├─────────────────────────────────────────────────────────────┤
│ 1. UserManager.initialise_tree(user_id, conversation_id)  │
│ 2. TreeManager.add_tree(conversation_id)                  │
│ 3. Creates Tree(settings=TreeManager.settings)            │
│ 4. Tree.__init__:                                         │
│    - Sets branch_initialisation (default: "one_branch")   │
│    - Calls one_branch_init()                              │
│    - Adds default tools to "base" branch:                 │
│      * CitedSummarizer                                     │
│      * FakeTextResponse                                    │
│      * Aggregate                                           │
│      * Query                                               │
│      * Visualise                                           │
│      * SummariseItems                                      │
│ 5. Tree ready to process queries                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Tool Availability (GET /tools/available)                   │
├─────────────────────────────────────────────────────────────┤
│ 1. discover_tools_from_module() inspects custom_tools     │
│ 2. Discovers all Tool subclasses including:               │
│    - Built-in tools (Query, Aggregate, etc.)              │
│    - Custom tools (TellAJoke, BasicLinearRegression)      │
│    - MCP tools (MCP_{server_name} for each enabled)       │
│ 3. Returns metadata for all discovered tools               │
└─────────────────────────────────────────────────────────────┘
```

## Key Files and Their Roles

| File | Purpose | Key Functions |
|------|---------|---------------|
| `elysia/api/app.py` | FastAPI application entry | Mounts routers, starts scheduler |
| `elysia/api/routes/init.py` | User/Tree initialization | `initialise_user()`, `initialise_tree()` |
| `elysia/api/routes/tools.py` | Tool discovery API | `/tools/available`, uses `discover_tools_from_module()` |
| `elysia/api/custom_tools.py` | Tool registration point | Imports all tools including MCP |
| `elysia/api/services/user.py` | User management | `UserManager.add_user_local()` |
| `elysia/api/services/tree.py` | Tree management | `TreeManager.add_tree()` |
| `elysia/tree/tree.py` | Decision tree core | `Tree.__init__()`, branch/tool management |
| `elysia/tools/mcp/mcp_loader.py` | MCP tool loading | `load_mcp_servers_from_config()` |
| `elysia/tools/mcp/mcp_tool.py` | MCP tool class | `MCPTool` class definition |
| `elysia/mcp.json` | MCP configuration | List of MCP servers to load |

## Default Settings Flow

### Settings Initialization Path

```
1. Environment Variables (.env file)
   ↓
2. elysia/config.py → environment_settings (singleton)
   ↓
3. Tree(settings=None) → uses environment_settings
   ↓
4. TreeManager(config=None) → creates Config()
   ↓
5. Config() → creates Settings() → uses environment_settings
   ↓
6. UserManager.add_user_local(config=None) → TreeManager gets default Config
```

### Default Tools in Tree

When `Tree()` is initialized with `branch_initialisation="one_branch"` (default):

**Branch "base" gets:**
- `CitedSummarizer` - Summarizes content with citations
- `FakeTextResponse` - Simple text response
- `Aggregate` - Aggregate/summarize data from knowledge base
- `Query` - Query knowledge base semantically
- `Visualise` - Create visualizations
- `SummariseItems` - Summarize retrieved items (linked to Query)

These tools are **always available** in a default Tree.

## MCP Tool Availability

### Current State
- **Configuration**: `elysia/mcp.json` with empty servers array
- **Available MCP Tools**: None (no servers enabled)
- **Status**: Infrastructure ready, awaiting server configuration

### To Enable MCP Tools

1. Edit `elysia/mcp.json`:
```json
{
  "servers": [
    {
      "name": "my_mcp_server",
      "description": "My custom MCP server",
      "server_script_path": "/path/to/mcp_server.py",
      "enabled": true
    }
  ]
}
```

2. Rebuild container:
```bash
docker-compose build elysia && docker-compose up -d elysia
```

3. Verify tool is available:
```bash
curl http://localhost:8000/tools/available
# Should show "MCP_my_mcp_server" in tools list
```

4. Use in Tree (programmatically):
```python
# The dynamically created class is already available
from elysia.api.custom_tools import MCP_my_mcp_server

tree = some_tree  # Get from TreeManager
mcp_tool = MCP_my_mcp_server()
tree.add_tool(mcp_tool, branch_id="base")
```

## Tool Discovery Mechanism

The `/tools/available` endpoint uses `discover_tools_from_module()` and `get_tool_metadata()` from `elysia/util/tool_discovery.py` which:

1. Inspects `custom_tools.__dict__`
2. Filters for classes that:
   - Are subclasses of `Tool`
   - Are not the base `Tool` class itself
3. Calls `get_metadata()` on each class
4. Returns metadata dict for all discovered tools

**MCP tools are discovered because:**
- `mcp_loader.__all__` lists all dynamically created classes
- `custom_tools.py` imports them into its namespace via:
  ```python
  for _mcp_tool_name in mcp_loader.__all__:
      globals()[_mcp_tool_name] = getattr(mcp_loader, _mcp_tool_name)
  ```

## Verification Tests

### Test 1: Tool Discovery ✓
```bash
curl http://localhost:8000/tools/available
# Returns: 6 tools (Query, Aggregate, etc.)
```

### Test 2: User Initialization ✓
```bash
curl -X POST http://localhost:8000/init/user/test_user_123
# Returns: user_exists=False, config with default settings
```

### Test 3: Tree Initialization ✓
```bash
curl -X POST http://localhost:8000/init/tree/test_user_123/test_conv_456 \
  -H "Content-Type: application/json" -d '{"low_memory": false}'
# Returns: tree initialized successfully
```

### Test 4: MCP Tool Loading (Ready)
```bash
# Edit mcp.json to enable a server, then:
curl http://localhost:8000/tools/available
# Should include MCP_* tool(s)
```

## Summary

✅ **Complete API flow established:**
- User initialization creates UserManager → TreeManager → Config → Settings
- Tree initialization creates Tree with default tools and Settings
- MCP tool loading infrastructure ready at application startup
- Tool discovery API exposes all available tools including MCP

✅ **MCP tools ready to be loaded:**
- Infrastructure in place
- Configuration file ready (`mcp.json`)
- No servers currently enabled
- When enabled, tools will be automatically discovered

✅ **Default tools available in Tree:**
- All standard Elysia tools loaded on Tree init
- Tools use Settings from TreeManager
- ClientManager available for tools needing external connections

🎯 **Next Steps (when needed):**
1. Create or locate MCP server script
2. Enable server in `mcp.json`
3. Rebuild container
4. MCP tools automatically available to all Trees

---

**Architecture Status: Complete and Functional** ✓

