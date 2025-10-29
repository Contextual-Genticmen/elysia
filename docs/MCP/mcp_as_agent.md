# MCP_AS_AGENT Configuration

## Overview

The `MCP_AS_AGENT` environment variable controls how MCP (Model Context Protocol) servers are integrated into Elysia.

**Transport**: Connects to running MCP servers via SSE/HTTP.

## Configuration

Add to your `.env` file:

```bash
# True:  Each MCP server becomes ONE agent tool (natural language interface)
# False: Each tool in the MCP server becomes an individual Elysia Tool
MCP_AS_AGENT=True
```

## Operating Modes

### Agent Mode (`MCP_AS_AGENT=True`) - Default

**Behavior:**
- One `MCPTool` instance per MCP server
- Takes **natural language queries** as input
- Uses **ReAct agent** with LangChain to execute tasks
- Agent has access to all tools in the MCP server
- Autonomous decision-making

**Tool Interface:**
```python
# Input Schema
{
    "query": "Natural language query or task description"
}

# Example Usage
tree("Use the MCP server to search for machine learning papers")
```

**Architecture:**
```
User Query (Natural Language)
    ↓
MCPTool (ReAct Agent)
    ↓
LangChain Agent Executor
    ├─→ MCP Tool 1
    ├─→ MCP Tool 2
    └─→ MCP Tool 3
         ↓
    Running MCP Server (HTTP/SSE)
```

### Individual Tool Mode (`MCP_AS_AGENT=False`)

**Behavior:**
- Each tool in the MCP server becomes a separate Elysia Tool
- Direct tool execution (no agent layer)
- Explicit tool selection required
- Structured inputs per tool

**Tool Interface:**
```python
# Each MCP tool gets its own Elysia Tool
# Example: mcp_server_search, mcp_server_analyze, etc.

# Input Schema (specific to each tool)
{
    "param1": "value1",
    "param2": "value2"
}

# Example Usage
tree.tools["mcp_server_search"](inputs={"query": "ML papers"})
```

**Architecture:**
```
Elysia Decision Tree
    ├─→ mcp_server_tool1 (Individual Elysia Tool)
    ├─→ mcp_server_tool2 (Individual Elysia Tool)
    └─→ mcp_server_tool3 (Individual Elysia Tool)
         ↓
    Running MCP Server (HTTP/SSE)
```

## Comparison

| Aspect | Agent Mode (True) | Individual Mode (False) |
|--------|------------------|------------------------|
| **Input Type** | Natural language | Structured parameters |
| **Tool Count** | 1 per server | N per server (N = # of MCP tools) |
| **Decision Making** | Autonomous (ReAct agent) | Manual (developer/user) |
| **Flexibility** | High (agent decides) | Low (explicit calls) |
| **Complexity** | Higher (agent overhead) | Lower (direct execution) |
| **Use Case** | Complex tasks, conversational | Simple tasks, workflows |
| **Dependencies** | langchain, langchain-openai | langchain-mcp-adapters only |
| **Transport** | SSE/HTTP to pre-running servers | SSE/HTTP to pre-running servers |

## Configuration

### MCP Server Configuration (`mcp.json`)

```json
{
  "research_assistant": {
    "url": "http://localhost:8000/sse",
    "headers": {
      "Authorization": "Bearer token123"
    }
  },
  "data_analyzer": {
    "url": "http://localhost:8001/sse",
    "headers": {}
  }
}
```

**Requirements:**
- MCP servers must be **pre-running** (not started by Elysia)
- Each server must expose SSE/HTTP endpoint
- Configure connection details in `mcp.json`

### Environment Setup

```bash
# .env file
MCP_AS_AGENT=True
BASE_MODEL=gpt-4
OPENAI_API_KEY=your_key_here
```

## Implementation Details

### Agent Mode Implementation

**MCPTool with Agent:**
```python
class MCPTool(Tool):
    def __init__(self, ...):
        if self.agent_mode:  # MCP_AS_AGENT=True
            self.inputs = {
                "query": {
                    "description": "Natural language query",
                    "type": str,
                    "required": True
                }
            }
    
    async def initialize(self):
        # Load MCP tools
        self._langchain_tools = await load_mcp_tools(session)
        
        if self.agent_mode:
            # Create ReAct agent
            from langchain.agents import create_react_agent, AgentExecutor
            llm = ChatOpenAI(...)
            agent = create_react_agent(llm, self._langchain_tools, prompt)
            self._agent = AgentExecutor(agent=agent, tools=self._langchain_tools)
    
    async def __call__(self, inputs, ...):
        if self.agent_mode:
            # Execute with agent
            result = await self._agent.ainvoke({"input": inputs["query"]})
            yield Text(result["output"])
```

### Individual Mode Implementation

**Individual Tool Wrappers:**
```python
class IndividualMCPToolWrapper(Tool):
    """Wrapper for a single MCP server tool."""
    
    def __init__(self, tool_name, ...):
        # Extract input schema from MCP tool
        super().__init__(
            name=f"mcp_{server_name}_{tool_name}",
            inputs={...},  # Tool-specific inputs
        )
    
    async def __call__(self, inputs, ...):
        # Connect to MCP server
        # Execute specific tool
        result = await self._langchain_tool.ainvoke(inputs)
        yield Result(result)
```

**Dynamic Tool Discovery:**
```python
def _create_individual_tool_wrappers(server_config):
    # Initialize temporary MCP connection
    temp_tool = MCPTool(...)
    await temp_tool.initialize()
    
    # Create wrapper for each discovered tool
    tool_classes = []
    for lc_tool in temp_tool._langchain_tools:
        wrapper = _create_individual_tool_class(
            tool_name=lc_tool.name,
            tool_description=lc_tool.description,
            ...
        )
        tool_classes.append(wrapper)
    
    return tool_classes
```

## Usage Examples

### Agent Mode Usage

```python
from elysia.tree import Tree
from elysia.tools.mcp.mcp_loader import load_mcp_servers_from_config
import os

os.environ["MCP_AS_AGENT"] = "True"

tools = load_mcp_servers_from_config()
tree = Tree(tools=tools)

# Natural language query
response = tree("Search for recent AI papers and analyze their sentiment")

# Agent will:
# 1. Decide to use 'search' tool
# 2. Execute search with appropriate parameters
# 3. Analyze results with 'analyze' tool
# 4. Return combined response
```

### Individual Mode Usage

```python
from elysia.tree import Tree
from elysia.tools.mcp.mcp_loader import load_mcp_servers_from_config
import os

os.environ["MCP_AS_AGENT"] = "False"

tools = load_mcp_servers_from_config()
tree = Tree(tools=tools)

# Direct tool invocation
search_results = tree.tools["api_ai_mcp_search"](
    inputs={"query": "AI papers", "limit": 10}
)

analysis_results = tree.tools["api_ai_mcp_analyze"](
    inputs={"text": search_results}
)
```

## Migration Guide

### From Individual to Agent Mode

**Before (Individual Mode):**
```python
# Explicit tool calls
tree.tools["mcp_server_tool1"](inputs={...})
tree.tools["mcp_server_tool2"](inputs={...})
```

**After (Agent Mode):**
```python
# Natural language query
tree("Use the tools to accomplish task X")
```

### From Agent to Individual Mode

**Before (Agent Mode):**
```python
tree("Search and analyze data")
```

**After (Individual Mode):**
```python
# Manual orchestration
results = tree.tools["mcp_server_search"](inputs={"query": "data"})
analysis = tree.tools["mcp_server_analyze"](inputs={"data": results})
```

## Troubleshooting

### Agent Mode Issues

**Problem:** Agent not making decisions correctly
- **Solution:** Adjust model (set BASE_MODEL env var to gpt-4 or better)
- **Solution:** Improve tool descriptions in MCP server

**Problem:** `ImportError: No module named 'langchain'`
- **Solution:** `pip install langchain langchain-openai`

**Problem:** Cannot connect to MCP server
- **Solution:** Ensure MCP server is running at configured URL
- **Solution:** Check `mcp.json` has correct URL and headers
- **Solution:** Verify network connectivity

### Individual Mode Issues

**Problem:** Tools not discovered
- **Solution:** Check MCP server is running and accessible
- **Solution:** Verify mcp.json configuration (URL, headers)
- **Solution:** Check logs for initialization errors

**Problem:** Tool inputs don't match schema
- **Solution:** Inspect tool schema: `tree.tools["server_tool"].inputs`
- **Solution:** Ensure MCP tool has proper input schema definition

**Problem:** Connection timeout
- **Solution:** Increase timeout in MCPTool configuration
- **Solution:** Verify server is responsive (test with curl)

## Best Practices

### When to Use Agent Mode

✅ Complex, multi-step tasks  
✅ Conversational interfaces  
✅ When tool selection logic is unclear  
✅ Autonomous task execution  
✅ Rapid prototyping  

### When to Use Individual Mode

✅ Predictable workflows  
✅ Performance-critical applications  
✅ Fine-grained error handling  
✅ Explicit control requirements  
✅ Debugging MCP tools  

### Server Management

- Always start MCP servers before initializing Elysia
- Use process managers (systemd, PM2) for production
- Monitor server health and connectivity
- Configure appropriate timeouts for long-running operations

## Performance Considerations

### Agent Mode
- **Latency:** Higher (agent reasoning + tool execution)
- **Cost:** Higher (LLM calls for agent reasoning)
- **Reliability:** Depends on agent model quality

### Individual Mode
- **Latency:** Lower (direct tool execution)
- **Cost:** Lower (no agent LLM calls)
- **Reliability:** Higher (deterministic execution)

## Dependencies

### Agent Mode Requirements
```bash
pip install langchain-mcp-adapters langchain langchain-openai
```

### Individual Mode Requirements
```bash
pip install langchain-mcp-adapters
```

## Summary

- **`MCP_AS_AGENT=True`**: AI agent interface, natural language, autonomous
- **`MCP_AS_AGENT=False`**: Direct tool access, structured inputs, manual control
- Default is `True` for ease of use
- Can switch modes without changing mcp.json
- Both modes use same MCP server configuration

---

**Choose Agent Mode for:** Flexibility, natural language, autonomous execution
**Choose Individual Mode for:** Control, performance, predictable workflows
