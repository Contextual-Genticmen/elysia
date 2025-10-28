# MCP (Model Context Protocol) Integration

Complete documentation for integrating MCP servers with Elysia.

## Quick Links

- **[Overview](overview.md)** - High-level summary of MCP integration
- **[Quickstart](quickstart.md)** - 30-second setup guide
- **[Architecture](architecture.md)** - Technical architecture details
- **[API Integration](api_integration.md)** - Complete API flow documentation
- **[Usage Guide](usage_guide.md)** - Configuration and usage instructions
- **[Implementation Details](implementation_details.md)** - Detailed changes, diagrams, and testing

## What is MCP Integration?

MCP (Model Context Protocol) integration allows Elysia to connect to external MCP-compliant tool servers, enabling:

- **Dynamic Tool Loading**: Add tools from MCP servers via configuration
- **Zero Code Changes**: Tools automatically discovered and registered
- **Consistent Interface**: All MCP tools follow Elysia's Tool interface
- **Isolation**: Each MCP server runs independently

## Quick Example

### 1. Configure MCP Server

Edit `elysia/mcp.json`:

```json
{
  "servers": [
    {
      "name": "my_server",
      "description": "My custom MCP server",
      "server_script_path": "/path/to/mcp_server.py",
      "enabled": true
    }
  ]
}
```

### 2. Rebuild Container

```bash
docker-compose build elysia && docker-compose up -d elysia
```

### 3. Use MCP Tools

Tools are automatically available to all Trees created via the API!

## Documentation Structure

### For Users

1. **Start with [Overview](overview.md)** - Understand what was built
2. **Read [Quickstart](quickstart.md)** - Get up and running quickly
3. **Review [Usage Guide](usage_guide.md)** - Learn configuration options

### For Developers

1. **Study [Architecture](architecture.md)** - Understand the implementation
2. **Review [API Integration](api_integration.md)** - See the complete flow
3. **Read [Implementation Details](implementation_details.md)** - See code changes and testing
4. **Refer to source code** in `elysia/tools/mcp/`

## Key Features

✅ **Automatic Discovery**: MCP tools are automatically discovered and registered  
✅ **API Integration**: Full integration with Elysia's UserManager and TreeManager  
✅ **Configuration-Based**: Enable/disable servers via `mcp.json`  
✅ **Production Ready**: Error handling, logging, type safety  
✅ **Minimal Code**: ~200 lines per component, no overengineering  

## Installation

The MCP integration uses `langchain-mcp-adapters`:

```bash
pip install langchain-mcp-adapters
```

This is already included in Elysia's dependencies.

## Current Status

- ✅ Integration complete and functional
- ✅ API flow tested and verified
- ✅ Documentation comprehensive
- ⏳ No MCP servers currently configured
- 🎯 Ready for production use

## Getting Help

- **Configuration Issues**: See [Usage Guide](usage_guide.md#troubleshooting)
- **Technical Details**: See [Architecture](architecture.md)
- **API Flow**: See [API Integration](api_integration.md)

---

**MCP integration is ready to use! Configure `mcp.json` to enable servers.** 🚀

