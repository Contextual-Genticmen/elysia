# MCP Integration - Architecture & Implementation

## Overview

Minimal MCP (Model Context Protocol) server integration for Elysia using `langchain-mcp-adapters`.

**Philosophy**: Use real libraries. No mock code. No overengineering. 300 lines total.

## Installation

```bash
pip install langchain-mcp-adapters
```

## Quick Implementation

```python
from elysia import Tree
from elysia.tools.additional import MCPServerAdapter

tree = Tree()
adapter = MCPServerAdapter(server_script_path="/path/to/server.py")
await adapter.initialize_and_register_tools(tree, branch_id="base")

# MCP tools now available
response, objects = tree("Use the search tool...")
```

---

## System Architecture

![MCP Architecture](../diagram/mcp_architecture.mmd)

> **View**: [MCP Architecture Diagram Source](../diagram/mcp_architecture.mmd)

**Key Components:**
- **MCPTool Gateway**: One instance per MCP server, acts as single entry point
- **LangChain Adapter**: Handles MCP protocol communication
- **MCP Server**: Your custom server (stdio) or remote service (SSE)
- **Individual Tools**: Discovered dynamically from MCP server

---

## Component Flow

### 1. Initialization Flow

```
User Code
    ↓
MCPServerAdapter.initialize()
    ↓
langchain-mcp-adapters.load_mcp_tools()
    ↓
StdioServerParameters + ClientSession
    ↓
Connect to MCP Server Script
    ↓
Load tools as LangChain tools
    ↓
For each LangChain tool:
    Create MCPToolWrapper
    ↓
Store in adapter.discovered_tools[]
```

### 2. Registration Flow

```
adapter.register_tools_with_tree(tree)
    ↓
For each MCPToolWrapper:
    ↓
    tree.add_tool(wrapper, branch_id)
        ↓
        Tool available in decision tree
```

### 3. Execution Flow

```
User: tree("Use search tool...")
    ↓
DecisionNode chooses 'mcp_search'
    ↓
MCPToolWrapper.__call__()
    ↓
langchain_tool.ainvoke(inputs)
    ↓
LangChain → MCP Server
    ↓
MCP Server executes tool
    ↓
Result returned
    ↓
MCPToolWrapper processes result
    ↓
Yield Result/Text/Error objects
    ↓
Response to user
```

---

## Implementation Details

### Components (300 lines total)

#### 1. MCPServerAdapter (176 lines)

```python
class MCPServerAdapter(Tool):
    - server_script_path: str
    - discovered_tools: list[MCPToolWrapper]
    
    Methods:
    + initialize()                    # Load tools from MCP server
    + register_tools_with_tree(tree)  # Register all tools
    + get_tool_by_name(name)          # Get specific tool
```

**Responsibilities:**
- Load tools from MCP server using `langchain-mcp-adapters`
- Create MCPToolWrapper for each tool
- Register tools with Elysia Tree

**Key implementation:**
```python
async def initialize(self) -> bool:
    from langchain_mcp_adapters.tools import load_mcp_tools
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    
    server_params = StdioServerParameters(
        command="python",
        args=[self.server_script_path],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            langchain_tools = await load_mcp_tools(session)
            
            for lc_tool in langchain_tools:
                wrapper = MCPToolWrapper(
                    langchain_tool=lc_tool,
                    logger=self.logger,
                )
                self.discovered_tools.append(wrapper)
    
    return True
```

#### 2. MCPToolWrapper (128 lines)

```python
class MCPToolWrapper(Tool):
    - langchain_tool: LangChain Tool
    - logger: Logger
    
    Methods:
    + __call__(inputs)           # Execute tool
    + is_tool_available()        # Check availability
```

**Responsibilities:**
- Wrap LangChain tool as Elysia Tool
- Convert input schemas
- Execute tool and process results
- Return Elysia objects (Result, Text, Error)

**Key implementation:**
```python
async def __call__(self, tree_data, inputs, base_lm, complex_lm, client_manager, **kwargs):
    yield Status(f"Executing {self.langchain_tool.name}...")
    
    try:
        if hasattr(self.langchain_tool, "ainvoke"):
            result = await self.langchain_tool.ainvoke(inputs)
        else:
            result = self.langchain_tool.invoke(inputs)
        
        # Process result
        if isinstance(result, str):
            yield Text(result)
        elif isinstance(result, dict):
            yield Result([result], name=self.langchain_tool.name)
        # ... more processing
        
    except Exception as e:
        yield Error(error_message=f"Error calling {self.langchain_tool.name}: {str(e)}")
```

---

## Usage Examples

### Basic: Register All Tools

```python
adapter = MCPServerAdapter(server_script_path="/path/to/server.py")
success, tools = await adapter.initialize_and_register_tools(tree)

if success:
    print(f"Registered {len(tools)} tools: {tools}")
```

### Selective: Register Specific Tools

```python
adapter = MCPServerAdapter(server_script_path="/path/to/server.py")
await adapter.initialize()

# List discovered tools
for tool in adapter.discovered_tools:
    print(f"{tool.name}: {tool.description}")

# Register only specific tools
search_tool = adapter.get_tool_by_name("search")
if search_tool:
    tree.add_tool(search_tool, branch_id="base")
```

### Multiple Servers

```python
servers = ["/path/to/server1.py", "/path/to/server2.py"]

for server_path in servers:
    adapter = MCPServerAdapter(server_script_path=server_path)
    await adapter.initialize_and_register_tools(tree)
```

---

## Design Principles Applied

Following **CODING_INSTRUCTIONS.md**:

✅ **Radical Minimalism**
- 300 lines total (was 2,000+ initially)
- Deleted 1,700+ lines of overengineered code
- No premature architecture

✅ **Use Real Libraries**
- Uses `langchain-mcp-adapters` directly
- No mock implementations
- No custom MCP clients

✅ **No Overengineering**
- 2 classes with clear responsibilities
- No factory patterns
- No unnecessary abstractions

✅ **Delete Aggressively**
- Removed mock MCP client implementations (250 lines)
- Removed factory functions (unnecessary abstraction)
- Removed HTTP client (not needed)
- Removed custom protocol handling (library handles it)

---

## What Was Removed

During refactoring, deleted:
- ❌ `langchain_client.py` (250 lines) - Mock MCP clients
- ❌ Factory functions - Single use abstraction
- ❌ HTTP client - Premature feature
- ❌ Custom schema conversions - Library handles it
- ❌ Complex result processing - Simplified

**Result: 85% code reduction (2,000 → 300 lines)**

---

## File Structure

```
elysia/tools/additional/
├── __init__.py                   # 3 lines - exports
├── mcp_adapter.py                # 176 lines - main adapter
├── mcp_tool_wrapper.py           # 128 lines - tool wrapper
├── ARCHITECTURE.md              # This file
└── QUICKSTART.md                # Quick reference

examples/
└── mcp_integration_example.py   # Working examples
```

---

## Data Flow Example

### Input
```python
tree("Search for documents about machine learning")
```

### Processing
```
1. DecisionNode selects 'mcp_search' tool
2. Inputs: {"query": "machine learning"}
3. MCPToolWrapper.__call__(inputs)
4. langchain_tool.ainvoke({"query": "machine learning"})
5. LangChain → MCP Server Script
6. MCP Server processes query
7. Returns: "Found 3 documents..."
8. MCPToolWrapper yields Text("Found 3 documents...")
```

### Output
```
Response: "Found 3 documents about machine learning"
Objects: [Text("Found 3 documents...")]
```

---

## Design Patterns

1. **Adapter Pattern**: MCPServerAdapter adapts MCP server interface to Elysia
2. **Wrapper Pattern**: MCPToolWrapper wraps LangChain tools as Elysia Tools
3. **Delegation Pattern**: Delegates to `langchain-mcp-adapters` for MCP interaction

---

## Error Handling

```python
# If langchain-mcp-adapters not installed
# Returns: False + logs "pip install langchain-mcp-adapters"

# If server script not found
# Returns: False + logs error message

# If tool execution fails
# Yields: Error object with details
```

---

## Testing Connection

```python
adapter = MCPServerAdapter(server_script_path="/path/to/server.py")
success = await adapter.initialize()

if success:
    print(f"✓ Connected! Loaded {len(adapter.discovered_tools)} tools")
    for tool in adapter.discovered_tools:
        print(f"  - {tool.name}")
else:
    print("✗ Failed to connect")
```

---

## Requirements

- Python 3.10+
- `langchain-mcp-adapters` package
- MCP server script (you implement)

---

## Key Benefits

1. **Minimal**: 300 lines vs. 2,000+ overengineered
2. **Functional**: Uses real library, actually works
3. **Maintainable**: Simple architecture, clear flow
4. **Standard**: Uses established patterns
5. **Honest**: Every line has a purpose

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Import error | `pip install langchain-mcp-adapters` |
| Server not found | Check `server_script_path` is correct |
| No tools loaded | Verify MCP server implements tools |
| Tool execution fails | Check tool inputs match schema |

---

## Code Stats

| Metric | Value |
|--------|-------|
| Total code lines | 307 |
| Files | 2 main + 1 init |
| Mock code | 0 lines |
| Abstraction layers | 2 (adapter, wrapper) |
| Dependencies | 1 (`langchain-mcp-adapters`) |
| Lines deleted | 1,700+ |

---

**Simple. Minimal. Actually works. 300 lines. No overengineering.**
