# MCP Implementation Details

This document combines detailed implementation information for the MCP integration, including changes, diagrams, and technical details.

## Changes Summary

### Quick Summary

**Problem**: MCP tools from `mcp.json` were not visible in the tree structure sent to the frontend.

**Solution**: Enhanced tool discovery to include MCP tools and auto-load them during tree initialization.

**Result**: MCP tools now automatically appear in the tree structure and are visible in the UI.

---

## Visual Flow Diagram

### Before Fix (Tools Not Visible)

```
┌─────────────────────────────────────────────────────────────────┐
│ Application Startup                                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ elysia/tools/mcp/mcp_loader.py                                  │
│ - Reads mcp.json                                                │
│ - Creates MCP_api_ai_mcp class                                  │
│ - Exports to module namespace                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Tree Initialization: Tree(branch_initialisation="one_branch")   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ set_branch_initialisation("one_branch")                         │
│   └─> load_default_tools_for_mode()                            │
│       └─> Adds: Query, Aggregate, Visualise, etc.              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ _load_additional_discovered_tools()                             │
│   └─> discover_tools_from_module()                             │
│       └─> Only searches: elysia.api.custom_tools               │
│           ❌ DOES NOT FIND MCP tools!                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ tree.tree structure                                             │
│ {                                                               │
│   "base": {                                                     │
│     "options": {                                                │
│       "query": {...},                                           │
│       "aggregate": {...}                                        │
│       ❌ NO MCP TOOLS                                           │
│     }                                                           │
│   }                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: GET /tree/{user_id}/{conversation_id}                 │
│   └─> Receives tree.tree                                       │
│       └─> MCP tools NOT VISIBLE in UI ❌                        │
└─────────────────────────────────────────────────────────────────┘
```

### After Fix (Tools Visible)

```
┌─────────────────────────────────────────────────────────────────┐
│ Application Startup                                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ elysia/tools/mcp/mcp_loader.py                                  │
│ - Reads mcp.json                                                │
│ - Creates MCP_api_ai_mcp class                                  │
│ - Exports to module namespace                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Tree Initialization: Tree(branch_initialisation="one_branch")   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ set_branch_initialisation("one_branch")                         │
│   └─> load_default_tools_for_mode()  ✨ ENHANCED               │
│       ├─> Adds default tools: Query, Aggregate, etc.           │
│       └─> 🆕 Auto-discover MCP tools:                           │
│           └─> discover_tools_from_module()  ✨ ENHANCED        │
│               ├─> Searches: elysia.api.custom_tools            │
│               └─> 🆕 Searches: elysia.tools.mcp.mcp_loader      │
│                   └─> ✅ FINDS: MCP_api_ai_mcp                  │
│                       └─> tree.add_tool(MCP_api_ai_mcp)        │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ tree.decision_nodes["base"].options                             │
│ {                                                               │
│   "query": {...},                                               │
│   "aggregate": {...},                                           │
│   "mcp_api_ai_mcp": {  ✅ MCP TOOL ADDED                        │
│     "description": "MCP server 'api-ai-mcp'...",               │
│     "action": <MCPTool instance>                               │
│   }                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ tree._construct_tree() builds tree.tree                         │
│ {                                                               │
│   "name": "Base",                                               │
│   "id": "base",                                                 │
│   "options": {                                                  │
│     "query": {...},                                             │
│     "aggregate": {...},                                         │
│     "mcp_api_ai_mcp": {  ✅ MCP TOOL IN TREE STRUCTURE          │
│       "name": "Mcp Api Ai Mcp",                                │
│       "description": "MCP server 'api-ai-mcp'...",             │
│       "branch": false                                           │
│     }                                                           │
│   }                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: GET /tree/{user_id}/{conversation_id}                 │
│   └─> Receives tree.tree                                       │
│       └─> ✅ MCP tools VISIBLE in UI!                           │
│           └─> User can select "Mcp Api Ai Mcp" tool            │
└─────────────────────────────────────────────────────────────────┘
```

## Files Changed

### 1. `elysia/util/tool_discovery.py`

**Function Modified**: `discover_tools_from_module()`

**Changes**:
- Added import of `elysia.tools.mcp.mcp_loader`
- Added logic to discover MCP tool classes from the mcp_loader module
- Filters for Tool subclasses with names starting with `MCP_`

**Impact**: MCP tools are now discovered alongside custom tools

### 2. `elysia/tools/ui/default_tools.py`

**Function Modified**: `load_default_tools_for_mode()`

**Changes**:
- Added auto-discovery of MCP tools after loading default tools
- Automatically adds discovered MCP tools to the root branch
- Logs successful and failed MCP tool additions

**Impact**: MCP tools are automatically added to every tree initialization

### 3. `elysia/tree/tree.py`

**Method Modified**: `_load_additional_discovered_tools()`

**Changes**:
- Removed duplicate MCP loading logic
- Converted to empty stub with deprecation notice
- Kept for backwards compatibility

**Impact**: Eliminates duplicate code; all MCP loading now centralized

## Transport Types Support

### Stdio Transport (Local MCP Server)
```python
tool = MCPTool(
    server_name="my_server",
    transport_type="stdio",
    server_script_path="/path/to/server.py"
)
```

### SSE Transport (Remote MCP Server)
```python
tool = MCPTool(
    server_name="api_server",
    transport_type="sse",
    url="http://localhost:8080/mcp",
    headers={"Authorization": "Bearer token"}
)
```

## Configuration Schema

### Stdio Transport Configuration
```json
{
  "name": "server_name",
  "description": "Server description",
  "type": "stdio",
  "server_script_path": "/path/to/script.py",
  "enabled": true
}
```

### SSE Transport Configuration
```json
{
  "name": "server_name",
  "description": "Server description",
  "type": "sse",
  "url": "http://host:port/path",
  "headers": {
    "Authorization": "Bearer token",
    "Custom-Header": "value"
  },
  "inputs": [
    {
      "type": "promptString",
      "id": "token_id",
      "description": "Token description",
      "password": true
    }
  ],
  "enabled": true
}
```

## Testing Checklist

- [x] MCP tools are discovered by `discover_tools_from_module()`
- [x] MCP tools are added to tree during initialization
- [x] MCP tools appear in `tree.tools` dictionary
- [x] MCP tools appear in `tree.decision_nodes[root].options`
- [x] MCP tools appear in `tree.tree` structure (what frontend sees)
- [x] Tool deduplication (`tools.py` uses `tool_discovery.py`)
- [x] Stdio transport support (local MCP servers)
- [x] SSE transport support (remote MCP servers)
- [x] Backwards compatibility maintained

## Key Benefits

1. **Automatic Discovery**: MCP tools are automatically discovered and added to trees
2. **No Manual Configuration**: No need to manually add MCP tools to tree branches
3. **Consistent Behavior**: All tree initialization modes get MCP tools automatically
4. **Frontend Visibility**: MCP tools now visible in UI for user selection
5. **Centralized Logic**: All tool loading logic in one place (`default_tools.py`)
6. **Multiple Transports**: Support for both local (stdio) and remote (SSE) MCP servers
7. **Type Safety**: Strong typing with Literal types for transport validation
8. **Extensibility**: Easy to add new transport types

## Future Enhancements

Potential improvements for future consideration:

1. **Selective Loading**: Allow configuration to specify which MCP tools to load
2. **Branch Placement**: Allow MCP tools to be added to specific branches, not just root
3. **Tool Ordering**: Control the order in which MCP tools appear in the tree
4. **Dynamic Reloading**: Hot-reload MCP tools when `mcp.json` changes
5. **Tool Metadata**: Extract and display MCP tool capabilities in UI
6. **Health Checks**: Monitor MCP server availability
7. **Failover**: Support fallback servers for high availability

---

**Implementation Status: Complete and Production-Ready** ✅



