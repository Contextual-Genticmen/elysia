"""
MCP Loader - Automatically loads MCP servers from mcp.json as Elysia Tools.
Supports both stdio and SSE transport types.
"""
import json
from pathlib import Path
from logging import getLogger

from elysia.tools.mcp.mcp_tool import MCPTool

logger = getLogger(__name__)


def load_mcp_servers_from_config() -> list[type[MCPTool]]:
    """
    Load MCP servers from mcp.json at module root (elysia/mcp.json).
    Each enabled server becomes one Elysia Tool class.
    
    Supports two transport types:
    - stdio: Runs a local MCP server script
    - sse: Connects to a remote MCP server via Server-Sent Events
    """
    config_path = Path(__file__).parent.parent.parent / "mcp.json"
    
    if not config_path.exists():
        logger.info("No mcp.json found at module root, skipping MCP server loading")
        return []
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        tool_classes = []
        servers = config.get("servers", [])
        
        for server_config in servers:
            if not server_config.get("enabled", False):
                continue
            
            server_name = server_config.get("name", "unknown")
            transport_type = server_config.get("type", "stdio")
            
            # Validate based on transport type
            if transport_type == "stdio":
                server_script = server_config.get("server_script_path")
                if not server_script:
                    logger.warning(f"MCP server '{server_name}' (stdio) missing server_script_path")
                    continue
                logger.info(f"Creating Elysia Tool for MCP server: {server_name} (stdio)")
                tool_class = _create_mcp_tool_class(
                    server_name=server_name,
                    transport_type="stdio",
                    server_script_path=server_script
                )
            elif transport_type == "sse":
                url = server_config.get("url")
                if not url:
                    logger.warning(f"MCP server '{server_name}' (sse) missing url")
                    continue
                headers = server_config.get("headers", {})
                logger.info(f"Creating Elysia Tool for MCP server: {server_name} (sse)")
                tool_class = _create_mcp_tool_class(
                    server_name=server_name,
                    transport_type="sse",
                    url=url,
                    headers=headers
                )
            else:
                logger.warning(f"Unknown transport type '{transport_type}' for server '{server_name}'")
                continue
            
            tool_classes.append(tool_class)
            logger.info(f"Created tool class: {tool_class.__name__}")
        
        return tool_classes
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid mcp.json format: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading MCP configuration: {e}")
        return []


def _create_mcp_tool_class(
    server_name: str,
    server_description: str,
    transport_type: str,
    server_script_path: str | None = None,
    url: str | None = None,
    headers: dict | None = None
) -> type[MCPTool]:
    """
    Dynamically create a Tool class for an MCP server.
    This creates a proper class that can be discovered by find_tool_classes.
    """
    # inject MCP prefix to distinguish from other tools
    class_name = f"MCP_{server_name}".replace("-", "_").replace(" ", "_")
    
    # Store references for the class
    _server_name = server_name
    _server_description = server_description
    _transport_type = transport_type
    _server_script_path = server_script_path
    _url = url
    _headers = headers or {}
    
    class DynamicMCPServer(MCPTool):
        """Dynamically created MCP server tool."""
        
        def __init__(self, **kwargs):
            init_kwargs = {
                "server_name": _server_name,
                "server_description": _server_description,
                "transport_type": _transport_type,
            }
            
            if _transport_type == "stdio":
                init_kwargs["server_script_path"] = _server_script_path
            elif _transport_type == "sse":
                init_kwargs["url"] = _url
                init_kwargs["headers"] = _headers
            
            super().__init__(**init_kwargs, **kwargs)
    
    # Set the class name
    DynamicMCPServer.__name__ = class_name
    DynamicMCPServer.__qualname__ = class_name
    
    return DynamicMCPServer


# Load servers at module import time
_loaded_tool_classes = load_mcp_servers_from_config()

# Export to module namespace for discovery
for tool_class in _loaded_tool_classes:
    globals()[tool_class.__name__] = tool_class

__all__ = [tool_class.__name__ for tool_class in _loaded_tool_classes]
