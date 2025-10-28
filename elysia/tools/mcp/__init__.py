# Export MCPTool for programmatic use
from .mcp_tool import MCPTool

# Auto-load MCP servers from mcp.json
from . import mcp_loader

# Don't export MCPTool by default to avoid it being discovered as a standalone tool
# Only the dynamically created server-specific classes from mcp_loader will be discovered
__all__ = []
