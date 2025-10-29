# MCP Implementation Details

This document provides comprehensive implementation information for the MCP integration, including architecture, interaction models, and technical details.

## MCP Tool Interaction Model

### Architecture Decision: MCP Server as Gateway Tool

**Key Concept**: Each `MCPTool` instance represents **one MCP server** that acts as a **gateway** to multiple underlying tools.

**Design Pattern**: Gateway + Two-Phase Execution
- **Phase 1**: Discovery - List available tools from the MCP server
- **Phase 2**: Execution - Execute a specific tool by name

**NOT**: Each MCP server tool as a separate Elysia Tool
**YES**: One Elysia Tool per MCP server, exposing multiple tools via actions

### Interaction Flow

```mermaid
graph TB
    subgraph "User/Agent Layer"
        User[User Query]
        Agent[Elysia Decision Agent]
    end
    
    subgraph "Elysia Tree Layer"
        Tree[Tree Instance]
        DecisionNode[Decision Node: 'base']
        Options[Available Options]
    end
    
    subgraph "MCPTool Gateway Layer"
        MCPTool[MCPTool Instance<br/>name: 'mcp_api_ai_mcp'<br/>One per MCP Server]
        Action{Action Type}
        ListAction[Action: 'list'<br/>Discover Tools]
        ExecAction[Action: 'execute'<br/>Run Specific Tool]
    end
    
    subgraph "LangChain Adapter Layer"
        LCAdapter[langchain-mcp-adapters]
        LCTools[LangChain Tools List<br/>tool1, tool2, tool3...]
    end
    
    subgraph "MCP Server Layer"
        MCPServer[MCP Server Process<br/>stdio or SSE]
        Tool1[MCP Tool: search]
        Tool2[MCP Tool: analyze]
        Tool3[MCP Tool: summarize]
    end
    
    User --> Agent
    Agent --> Tree
    Tree --> DecisionNode
    DecisionNode --> Options
    Options --> MCPTool
    
    MCPTool --> Action
    Action -->|action='list'| ListAction
    Action -->|action='execute'| ExecAction
    
    ListAction --> LCAdapter
    ExecAction --> LCAdapter
    
    LCAdapter --> MCPServer
    
    MCPServer --> Tool1
    MCPServer --> Tool2
    MCPServer --> Tool3
    
    LCTools -.cached in.-> MCPTool
    
    style MCPTool fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style Agent fill:#9B59B6,stroke:#7D3C98,color:#fff
    style LCAdapter fill:#F39C12,stroke:#D68910,color:#fff
    style MCPServer fill:#E74C3C,stroke:#C0392B,color:#fff
```

### Parameter Surfacing Model

```mermaid
sequenceDiagram
    participant Agent as Elysia Agent
    participant MCPTool as MCPTool Gateway
    participant Init as initialize()
    participant LC as LangChain Tools
    participant MCP as MCP Server
    
    Note over Agent,MCP: Phase 1: Discovery & Initialization
    
    Agent->>MCPTool: First call (any action)
    MCPTool->>Init: Check _initialized flag
    Init->>LC: load_mcp_tools(session)
    LC->>MCP: Connect via stdio/SSE
    MCP-->>LC: Return tool list with schemas
    LC-->>Init: LangChain tool objects
    Init->>MCPTool: Cache tools in _langchain_tools[]
    Note over MCPTool: Tools cached for reuse
    
    Note over Agent,MCP: Phase 2a: List Tools (Discovery)
    
    Agent->>MCPTool: Call with action='list'
    MCPTool->>MCPTool: Extract tool metadata
    Note over MCPTool: For each cached LangChain tool:<br/>name, description, input schema
    MCPTool-->>Agent: Result([{name, description, inputs}])
    
    Note over Agent,MCP: Phase 2b: Execute Tool
    
    Agent->>MCPTool: Call with action='execute'<br/>+ tool_name='search'<br/>+ tool_inputs={query: "..."}
    MCPTool->>MCPTool: get_tool_by_name('search')
    MCPTool->>LC: langchain_tool.ainvoke(tool_inputs)
    LC->>MCP: Execute 'search' with inputs
    MCP-->>LC: Tool result
    LC-->>MCPTool: Result data
    MCPTool-->>Agent: Result/Text/Error objects
```

### Why This Design?

**Advantages of Gateway Pattern:**

1. **Single Tool Registration**: One MCPTool per server instead of N separate tools
2. **Dynamic Discovery**: Tools can change without code regeneration
3. **Lazy Loading**: Connect to MCP server only when first used
4. **Unified Management**: Single point for monitoring, logging, error handling
5. **Tool Metadata Access**: Agent can query available tools before execution

**Alternative Rejected: Individual Tool Wrapping**
```python
# ❌ NOT IMPLEMENTED: Each MCP tool as separate Elysia tool
tree.add_tool(MCPSearchTool())      # Would need separate class
tree.add_tool(MCPAnalyzeTool())     # Would need separate class
tree.add_tool(MCPSummarizeTool())   # Would need separate class

# ✅ IMPLEMENTED: Gateway pattern
tree.add_tool(MCPTool(server_name="api_ai_mcp"))  # One tool, multiple capabilities
```

## Changes Summary

### Quick Summary

**Problem**: MCP tools from `mcp.json` were not visible in the tree structure sent to the frontend.

**Solution**: Enhanced tool discovery to include MCP tools and auto-load them during tree initialization.

**Result**: MCP tools now automatically appear in the tree structure and are visible in the UI.

---

## Tool Discovery & Loading Flow

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
## Tool Discovery & Loading Flow

### Before Fix (Tools Not Visible)

```mermaid
flowchart TD
    Start([Application Startup]) --> LoadMCP[elysia/tools/mcp/mcp_loader.py<br/>Reads mcp.json<br/>Creates MCP classes]
    LoadMCP --> TreeInit[Tree Initialization<br/>branch_initialisation='one_branch']
    TreeInit --> SetBranch[set_branch_initialisation]
    SetBranch --> LoadDefault[load_default_tools_for_mode<br/>Adds: Query, Aggregate, etc.]
    LoadDefault --> DiscoverAdditional[_load_additional_discovered_tools]
    DiscoverAdditional --> SearchCustom[discover_tools_from_module<br/>Only searches: elysia.api.custom_tools]
    SearchCustom --> NoMCP[❌ DOES NOT FIND MCP tools!]
    NoMCP --> BuildTree[tree.tree structure<br/>NO MCP TOOLS]
    BuildTree --> Frontend[Frontend GET /tree/user/conversation<br/>❌ MCP tools NOT VISIBLE]
    
    style NoMCP fill:#ffcccc,stroke:#cc0000
    style Frontend fill:#ffcccc,stroke:#cc0000
    style BuildTree fill:#ffeecc,stroke:#cc6600
```

### After Fix (Tools Visible)

```mermaid
flowchart TD
    Start([Application Startup]) --> LoadMCP[elysia/tools/mcp/mcp_loader.py<br/>Reads mcp.json<br/>Creates MCP classes]
    LoadMCP --> TreeInit[Tree Initialization<br/>branch_initialisation='one_branch']
    TreeInit --> SetBranch[set_branch_initialisation]
    SetBranch --> LoadDefault[load_default_tools_for_mode ✨<br/>Adds: Query, Aggregate, etc.]
    LoadDefault --> AutoDiscover[🆕 Auto-discover MCP tools]
    AutoDiscover --> SearchMCP[discover_tools_from_module<br/>Searches: elysia.tools.mcp.mcp_loader]
    SearchMCP --> FoundMCP[✅ FINDS: MCP_api_ai_mcp]
    FoundMCP --> AddTool[tree.add_tool MCP_api_ai_mcp]
    AddTool --> UpdateNode[tree.decision_nodes base.options<br/>mcp_api_ai_mcp added]
    UpdateNode --> BuildTree[tree._construct_tree<br/>MCP TOOLS IN STRUCTURE]
    BuildTree --> Frontend[Frontend GET /tree/user/conversation<br/>✅ MCP tools VISIBLE in UI]
    
    style FoundMCP fill:#ccffcc,stroke:#00cc00
    style Frontend fill:#ccffcc,stroke:#00cc00
    style BuildTree fill:#eeffcc,stroke:#66cc00
    style AutoDiscover fill:#cceeff,stroke:#0066cc
```

## MCPTool Input/Output Contract

### Tool Definition (What Agent Sees)

```mermaid
classDiagram
    class MCPTool {
        +name: str = "mcp_server_name"
        +description: str = "MCP server '...' provides access to multiple tools"
        +status: str = "Ready to connect"
        +inputs: dict
        +end: bool = False
        
        +initialize() bool
        +__call__(inputs) AsyncGenerator
        +get_tool_by_name(name) Tool
        +is_tool_available() bool
    }
    
    class ToolInputs {
        action: str = "list|execute"
        tool_name: Optional~str~
        tool_inputs: Optional~dict~
    }
    
    class ToolOutputs {
        Status: "Initializing..."
        Result: List~dict~
        Text: str
        Error: str
    }
    
    MCPTool --> ToolInputs : expects
    MCPTool --> ToolOutputs : yields
    
    note for MCPTool "Single gateway to multiple MCP tools<br/>Agent sees ONE tool per MCP server"
    note for ToolInputs "action='list': Discover tools<br/>action='execute': Run specific tool"
```

### Input Schema Surfacing

The agent receives this schema in `DecisionPrompt.available_actions`:

```python
{
    "name": "mcp_api_ai_mcp",
    "description": "MCP server 'api-ai-mcp' (stdio) - provides access to multiple tools",
    "inputs": {
        "action": {
            "description": "Action: 'list' to show tools, 'execute' to run a specific tool",
            "type": "<class 'str'>",
            "default": "list"
        },
        "tool_name": {
            "description": "Name of the tool to execute (required when action='execute')",
            "type": "<class 'str'>",
            "required": False
        },
        "tool_inputs": {
            "description": "Inputs for the tool (required when action='execute')",
            "type": "<class 'dict'>",
            "required": False,
            "default": {}
        }
    }
}
```

### Execution Patterns

#### Pattern 1: Discovery First

```mermaid
sequenceDiagram
    participant Agent
    participant MCPTool
    participant MCPServer
    
    Agent->>MCPTool: action='list'
    activate MCPTool
    MCPTool->>MCPServer: Connect & discover
    MCPServer-->>MCPTool: [search, analyze, summarize]
    MCPTool-->>Agent: Result([{name: 'search', ...}, ...])
    deactivate MCPTool
    
    Note over Agent: Agent sees available tools<br/>and their input schemas
    
    Agent->>MCPTool: action='execute'<br/>tool_name='search'<br/>tool_inputs={query: "ML"}
    activate MCPTool
    MCPTool->>MCPServer: Execute 'search' tool
    MCPServer-->>MCPTool: Search results
    MCPTool-->>Agent: Text("Found 3 documents...")
    deactivate MCPTool
```

#### Pattern 2: Direct Execution

```mermaid
sequenceDiagram
    participant Agent
    participant MCPTool
    participant MCPServer
    
    Note over Agent: Agent already knows<br/>tool name from config
    
    Agent->>MCPTool: action='execute'<br/>tool_name='analyze'<br/>tool_inputs={text: "..."}
    activate MCPTool
    MCPTool->>MCPTool: Initialize if needed
    MCPTool->>MCPServer: Execute 'analyze' tool
    MCPServer-->>MCPTool: Analysis result
    MCPTool-->>Agent: Result([{sentiment: 0.8, ...}])
    deactivate MCPTool
```

## Parameter Flow: From Configuration to Execution

```mermaid
flowchart LR
    subgraph "1. Configuration"
        JSON[mcp.json<br/>server_script_path<br/>url, headers, etc.]
    end
    
    subgraph "2. Tool Creation"
        Loader[mcp_loader.py<br/>Creates MCPTool class]
        Instance[MCPTool instance<br/>with config params]
    end
    
    subgraph "3. Tree Registration"
        Discovery[Tool Discovery<br/>discover_tools_from_module]
        TreeAdd[tree.add_tool<br/>MCPTool instance]
    end
    
    subgraph "4. Agent Decision"
        Schema[DecisionPrompt<br/>available_actions with inputs]
        AgentChoice[Agent selects tool<br/>+ provides inputs]
    end
    
    subgraph "5. Execution"
        Call[MCPTool.__call__<br/>action, tool_name, tool_inputs]
        MCPExec[MCP Server execution]
    end
    
    JSON --> Loader
    Loader --> Instance
    Instance --> Discovery
    Discovery --> TreeAdd
    TreeAdd --> Schema
    Schema --> AgentChoice
    AgentChoice --> Call
    Call --> MCPExec
    
    style JSON fill:#e1f5ff
    style Schema fill:#fff4e6
    style MCPExec fill:#e8f5e9
```

## Two-Phase Parameter Surfacing

### Phase 1: MCPTool Parameters (Elysia Level)

These are **always** visible to the agent in `available_actions`:

```python

## Two-Phase Parameter Surfacing

### Phase 1: MCPTool Parameters (Elysia Level)

These are **always** visible to the agent in `available_actions`:

```python
{
    "action": "list" | "execute",      # What to do with the MCP server
    "tool_name": "optional_string",    # Which MCP tool to run (if execute)
    "tool_inputs": {"key": "value"}    # Inputs for that specific tool
}
```

### Phase 2: MCP Tool Parameters (MCP Server Level)

These are **discovered dynamically** when `action='list'`:

```python
# Agent calls: MCPTool(action='list')
# Returns:
[
    {
        "name": "search",
        "description": "Search documents",
        "inputs": {
            "query": "string",
            "limit": "int"
        }
    },
    {
        "name": "analyze",
        "description": "Analyze sentiment",
        "inputs": {
            "text": "string"
        }
    }
]
```

Then agent uses this info to call:
```python
MCPTool(
    action='execute',
    tool_name='search',
    tool_inputs={'query': 'ML papers', 'limit': 10}
)
```

## Real-World Execution Example

### Complete Flow with Parameter Surfacing

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant A as Agent/Tree
    participant D as DecisionPrompt
    participant M as MCPTool
    participant L as LangChain
    participant S as MCP Server
    
    U->>A: "Find ML papers and analyze sentiment"
    
    Note over A,D: Decision Phase
    A->>D: Build DecisionPrompt with available_actions
    D->>D: available_actions includes:<br/>{name: "mcp_api_ai_mcp"<br/>inputs: {action, tool_name, tool_inputs}}
    D->>A: Select "mcp_api_ai_mcp" + inputs
    
    Note over A,M: Discovery Phase
    A->>M: __call__(action='list')
    M->>M: initialize() if needed
    M->>L: Connect to MCP server
    L->>S: Discover available tools
    S-->>L: [search_tool, analyze_tool, ...]
    L-->>M: LangChain tool objects with schemas
    M-->>A: Result([{name: "search", inputs: {...}}, ...])
    
    Note over A: Agent now knows MCP tools<br/>and their schemas
    
    Note over A,M: Execution Phase 1: Search
    A->>M: __call__(action='execute',<br/>tool_name='search',<br/>tool_inputs={query: "ML papers"})
    M->>L: langchain_tool.ainvoke({query: "ML papers"})
    L->>S: Execute search_tool
    S-->>L: ["Paper 1", "Paper 2", ...]
    L-->>M: Result data
    M-->>A: Text("Found 3 ML papers...")
    
    Note over A,M: Execution Phase 2: Analyze
    A->>M: __call__(action='execute',<br/>tool_name='analyze',<br/>tool_inputs={text: "Paper 1 content"})
    M->>L: langchain_tool.ainvoke({text: "..."})
    L->>S: Execute analyze_tool
    S-->>L: {sentiment: 0.85, ...}
    L-->>M: Analysis result
    M-->>A: Result([{sentiment: 0.85}])
    
    A-->>U: "Found 3 papers. Sentiment analysis shows positive..."
```

## Architecture Comparison

### Design Choice: Why Gateway Pattern?

```mermaid
graph TB
    subgraph "❌ Alternative: Individual Tool Wrapping (NOT USED)"
        A1[Tree] --> B1[MCPSearchTool]
        A1 --> B2[MCPAnalyzeTool]
        A1 --> B3[MCPSummarizeTool]
        B1 --> C1[MCP Server 1]
        B2 --> C1
        B3 --> C1
        
        note1[Issues:<br/>- N separate tool classes<br/>- Duplicate connection logic<br/>- No dynamic discovery<br/>- Code regeneration needed]
    end
    
    subgraph "✅ Implemented: Gateway Pattern"
        A2[Tree] --> B4[MCPTool Gateway]
        B4 --> |action='list'| C2[Discover Tools]
        B4 --> |action='execute'<br/>tool_name='search'| C2
        B4 --> |action='execute'<br/>tool_name='analyze'| C2
        C2 --> D2[MCP Server]
        
        note2[Benefits:<br/>+ One tool per server<br/>+ Single connection<br/>+ Dynamic discovery<br/>+ No code generation]
    end
    
    style note1 fill:#ffcccc,stroke:#cc0000
    style note2 fill:#ccffcc,stroke:#00cc00
```

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

### Transport Architecture

```mermaid
graph TB
    subgraph "MCPTool Configuration"
        Config[MCPTool Instance]
        TransportType{transport_type}
    end
    
    subgraph "Stdio Transport (Local)"
        Stdio[StdioServerParameters]
        StdioClient[stdio_client]
        LocalScript[Local Python Script<br/>server.py]
        
        StdioConfig[Configuration:<br/>- server_script_path: str<br/>- command: 'python']
    end
    
    subgraph "SSE Transport (Remote)"
        SSE[SSE Configuration]
        SSEClient[sse_client]
        RemoteServer[Remote HTTP Server<br/>http://host:port/mcp]
        
        SSEConfig[Configuration:<br/>- url: str<br/>- headers: dict]
    end
    
    subgraph "Common MCP Layer"
        Session[ClientSession]
        Protocol[MCP Protocol]
        Tools[load_mcp_tools]
    end
    
    Config --> TransportType
    TransportType -->|type='stdio'| Stdio
    TransportType -->|type='sse'| SSE
    
    Stdio --> StdioConfig
    StdioConfig --> StdioClient
    StdioClient --> LocalScript
    LocalScript --> Session
    
    SSE --> SSEConfig
    SSEConfig --> SSEClient
    SSEClient --> RemoteServer
    RemoteServer --> Session
    
    Session --> Protocol
    Protocol --> Tools
    
    style Stdio fill:#e8f5e9,stroke:#4CAF50
    style SSE fill:#e3f2fd,stroke:#2196F3
    style Session fill:#fff9c4,stroke:#FBC02D
```

### Stdio Transport (Local MCP Server)
```python
tool = MCPTool(
    server_name="my_server",
    transport_type="stdio",
    server_script_path="/path/to/server.py"
)
```

**Use Case**: Local development, custom scripts, file system tools

### SSE Transport (Remote MCP Server)
```python
tool = MCPTool(
    server_name="api_server",
    transport_type="sse",
    url="http://localhost:8080/mcp",
    headers={"Authorization": "Bearer token"}
)
```

**Use Case**: API integrations, cloud services, remote tools

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

## Summary: How MCPTool Works

### Key Points

1. **One Tool Per Server**: Each `MCPTool` instance = one MCP server gateway
2. **Two-Phase Operation**: 
   - `action='list'`: Discover available tools
   - `action='execute'`: Run a specific tool
3. **Dynamic Discovery**: Tools are discovered at runtime, no code generation
4. **Gateway Pattern**: Agent interacts with ONE tool that proxies to many MCP tools
5. **Parameter Surfacing**: 
   - **Elysia Level**: action, tool_name, tool_inputs (always visible)
   - **MCP Level**: Each tool's specific parameters (discovered dynamically)

### Agent's View

```python
# The agent sees this in available_actions:
{
    "name": "mcp_api_ai_mcp",
    "description": "MCP server providing multiple tools",
    "inputs": {
        "action": "list or execute",
        "tool_name": "string (optional)",
        "tool_inputs": "dict (optional)"
    }
}

# Agent can:
# 1. List tools: MCPTool(action='list')
# 2. Execute tool: MCPTool(action='execute', tool_name='search', tool_inputs={...})
```

### Developer's View

```python
# Configuration (mcp.json)
{
    "name": "my_server",
    "type": "stdio",
    "server_script_path": "/path/to/server.py"
}

# Results in MCPTool class creation
class MCP_my_server(MCPTool):
    def __init__(self):
        super().__init__(
            server_name="my_server",
            transport_type="stdio",
            server_script_path="/path/to/server.py"
        )

# Automatically discovered and added to tree
# Agent can now use it without any manual registration
```

### Execution Flow Summary

```mermaid
graph LR
    A[1. Configuration<br/>mcp.json] --> B[2. MCPTool Class<br/>Auto-generated]
    B --> C[3. Tool Discovery<br/>Auto-loaded to tree]
    C --> D[4. Agent Decision<br/>Selects MCPTool]
    D --> E[5. Initialize<br/>Connect to MCP server]
    E --> F[6. Action: list/execute<br/>Discover or run tools]
    F --> G[7. Result<br/>Return to agent]
    
    style A fill:#e1f5ff
    style D fill:#fff4e6
    style F fill:#e8f5e9
    style G fill:#f3e5f5
```

## Key Benefits

1. **Automatic Discovery**: MCP tools are automatically discovered and added to trees
2. **No Manual Configuration**: No need to manually add MCP tools to tree branches
3. **Consistent Behavior**: All tree initialization modes get MCP tools automatically
4. **Frontend Visibility**: MCP tools now visible in UI for user selection
5. **Centralized Logic**: All tool loading logic in one place (`default_tools.py`)
6. **Multiple Transports**: Support for both local (stdio) and remote (SSE) MCP servers
7. **Type Safety**: Strong typing with Literal types for transport validation
8. **Extensibility**: Easy to add new transport types
9. **Gateway Pattern**: One tool per server, not N tools per server
10. **Dynamic Capabilities**: Tools discovered at runtime, adapts to server changes

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



