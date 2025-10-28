"""
MCP Tool - Single Elysia Tool class for MCP server integration.

Each instance represents one MCP server and provides access to all its tools.
Supports both stdio and SSE transports.
"""
from __future__ import annotations
from typing import Any, AsyncGenerator, TYPE_CHECKING, Literal
from logging import Logger, getLogger

import dspy

from elysia.objects import Tool, Status, Error, Text, Result
from elysia.tree.objects import TreeData
from elysia.util.client import ClientManager

if TYPE_CHECKING:
    from elysia.tree.tree import Tree

logger = getLogger(__name__)


class MCPTool(Tool):
    """
    Elysia Tool that connects to an MCP server and provides access to all its tools.
    
    Each instance represents one MCP server. The tool can list available tools
    or execute specific tools by name.
    
    Supports two transport types:
    - stdio: Runs a local MCP server script
    - sse: Connects to a remote MCP server via Server-Sent Events
    
    Usage:
        # Stdio transport
        tool = MCPTool(
            server_name="my_server",
            transport_type="stdio",
            server_script_path="/path/to/server.py",
            server_description="My custom MCP server for XYZ"
        )
        
        # SSE transport
        tool = MCPTool(
            server_name="api_server",
            transport_type="sse",
            url="http://localhost:8080/mcp",
            headers={"Authorization": "Bearer token"},
            server_description="Remote MCP server with AI capabilities"
        )
    """

    def __init__(
        self,
        server_name: str,
        transport_type: Literal["stdio", "sse"] = "stdio",
        server_script_path: str | None = None,
        url: str | None = None,
        headers: dict[str, str] | None = None,
        server_description: str | None = None,
        logger: Logger | None = None,
        **kwargs,
    ):
        """
        Args:
            server_name: Name identifier for this MCP server
            transport_type: Transport type ("stdio" or "sse")
            server_script_path: Path to the MCP server script (required for stdio)
            url: URL for SSE endpoint (required for sse)
            headers: HTTP headers for SSE connection (optional for sse)
            server_description: Custom description for the MCP server (optional)
            logger: Optional logger
        """
        self.server_name = server_name
        self.transport_type = transport_type
        self.server_script_path = server_script_path
        self.url = url
        self.headers = headers or {}
        self.logger = logger or globals()['logger']
        self._langchain_tools: list[Any] = []
        self._initialized = False

        # Validation
        if transport_type == "stdio" and not server_script_path:
            raise ValueError("server_script_path is required for stdio transport")
        if transport_type == "sse" and not url:
            raise ValueError("url is required for sse transport")

        # Use custom description if provided, otherwise use generic one
        if server_description:
            description = server_description
        else:
            description = f"MCP server '{server_name}' ({transport_type}) - provides access to multiple tools via Model Context Protocol"

        super().__init__(
            name=f"mcp_{server_name}",
            description=description,
            status="Ready to connect to MCP server",
            inputs={
                "action": {
                    "description": "Action: 'list' to show tools, 'execute' to run a specific tool",
                    "type": str,
                    "default": "list",
                },
                "tool_name": {
                    "description": "Name of the tool to execute (required when action='execute')",
                    "type": str,
                    "required": False,
                },
                "tool_inputs": {
                    "description": "Inputs for the tool (required when action='execute')",
                    "type": dict,
                    "required": False,
                    "default": {},
                },
            },
            end=False,
            **kwargs,
        )

    async def initialize(self) -> bool:
        """Initialize connection and discover tools from MCP server."""
        if self._initialized:
            return True

        try:
            if self.logger:
                self.logger.info(f"Loading tools from MCP server: {self.server_name} ({self.transport_type})")

            from langchain_mcp_adapters.tools import load_mcp_tools
            from mcp import ClientSession

            if self.transport_type == "stdio":
                from mcp import StdioServerParameters
                from mcp.client.stdio import stdio_client

                server_params = StdioServerParameters(
                    command="python",
                    args=[self.server_script_path],
                )

                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self._langchain_tools = await load_mcp_tools(session)

            elif self.transport_type == "sse":
                from mcp.client.sse import sse_client
                
                async with sse_client(self.url, headers=self.headers) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self._langchain_tools = await load_mcp_tools(session)

            self._initialized = True
            
            if self.logger:
                self.logger.info(f"Loaded {len(self._langchain_tools)} tools from {self.server_name}")

            return True

        except ImportError as e:
            if self.logger:
                self.logger.error(f"langchain-mcp-adapters not installed: {e}")
                self.logger.error("Install with: pip install langchain-mcp-adapters")
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize MCP server '{self.server_name}': {str(e)}")
            return False

    def get_tool_by_name(self, tool_name: str) -> Any | None:
        """Get a specific LangChain tool by name."""
        for tool in self._langchain_tools:
            if getattr(tool, "name", "") == tool_name:
                return tool
        return None
 
    async def __call__(
        self,
        tree_data: TreeData,
        inputs: dict,
        base_lm: dspy.LM,
        complex_lm: dspy.LM,
        client_manager: ClientManager | None = None,
        **kwargs,
    ) -> AsyncGenerator[Result | Status | Error | Text, None]:
        """Execute actions: list tools or execute a specific tool."""
        action = inputs.get("action", "list")

        # Initialize if needed
        if not self._initialized:
            yield Status(f"Initializing MCP server '{self.server_name}'...")
            success = await self.initialize()
            if not success:
                yield Error(error_message=f"Failed to initialize MCP server '{self.server_name}'")
                return

        # List available tools
        if action == "list":
            tool_info = [
                {
                    "name": getattr(t, "name", "unknown"),
                    "description": getattr(t, "description", "No description"),
                }
                for t in self._langchain_tools
            ]
            yield Result(tool_info, name=f"{self.server_name}_tools")
            yield Text(
                f"MCP Server '{self.server_name}' has {len(self._langchain_tools)} tools:\n"
                + "\n".join([f"- {t['name']}: {t['description']}" for t in tool_info])
            )

        # Execute a specific tool
        elif action == "execute":
            tool_name = inputs.get("tool_name")
            tool_inputs = inputs.get("tool_inputs", {})

            if not tool_name:
                yield Error(error_message="tool_name is required when action='execute'")
                return

            # Find the tool
            lc_tool = self.get_tool_by_name(tool_name)
            if not lc_tool:
                available = [getattr(t, "name", "") for t in self._langchain_tools]
                yield Error(
                    error_message=f"Tool '{tool_name}' not found. Available: {available}"
                )
                return

            # Execute the tool
            yield Status(f"Executing '{tool_name}' on MCP server '{self.server_name}'...")

            try:
                if hasattr(lc_tool, "ainvoke"):
                    result = await lc_tool.ainvoke(tool_inputs)
                else:
                    result = lc_tool.invoke(tool_inputs)

                if self.logger:
                    self.logger.debug(f"Tool '{tool_name}' result: {result}")

                # Process result
                if isinstance(result, str):
                    yield Text(result)
                elif isinstance(result, dict):
                    yield Result([result], name=tool_name)
                elif isinstance(result, list):
                    yield Result(
                        [item if isinstance(item, dict) else {"value": item} for item in result],
                        name=tool_name,
                    )
                else:
                    yield Result([{"result": str(result)}], name=tool_name)

            except Exception as e:
                error_msg = f"Error executing '{tool_name}' on '{self.server_name}': {str(e)}"
                if self.logger:
                    self.logger.error(error_msg)
                yield Error(error_message=error_msg)

        else:
            yield Error(error_message=f"Unknown action '{action}'. Use 'list' or 'execute'")

    async def is_tool_available(
        self,
        tree_data: TreeData,
        base_lm: dspy.LM,
        complex_lm: dspy.LM,
        client_manager: ClientManager,
    ) -> bool:
        """Check if the MCP server is available."""
        return bool(self.server_script_path)

