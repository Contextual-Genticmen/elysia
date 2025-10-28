from elysia import Tool
from elysia.objects import Response

# Import a custom tool from a separate file
from elysia.tools.visualisation.linear_regression import BasicLinearRegression

# Import existing tools
from elysia.tools.retrieval.query import Query
from elysia.tools.retrieval.aggregate import Aggregate
from elysia.tools.text.text import CitedSummarizer, FakeTextResponse

# Import MCP servers dynamically loaded from mcp.json
# Each enabled server becomes one Elysia Tool
from elysia.tools.mcp import mcp_loader  # noqa: F401

# Import all dynamically created MCP tool classes into this module's namespace
# so find_tool_classes() can discover them
for _mcp_tool_name in mcp_loader.__all__:
    globals()[_mcp_tool_name] = getattr(mcp_loader, _mcp_tool_name)


# Or you can define the tool inline here
class TellAJoke(Tool):
    """
    Example tool for testing/demonstration purposes.
    Simply returns a joke as a text response that was an input to the tool.
    """

    def __init__(self, **kwargs):

        # Init requires initialisation of the super class (Tool)
        super().__init__(
            name="tell_a_joke",
            description="Displays a joke to the user.",
            inputs={
                "joke": {
                    "type": str,
                    "description": "A joke to tell.",
                    "required": True,
                }
            },
            end=True,
        )

    # Call must be a async generator function that yields objects to the decision tree
    async def __call__(
        self, tree_data, inputs, base_lm, complex_lm, client_manager, **kwargs
    ):

        # This example tool only returns the input to the tool, so is not very useful
        yield Response(inputs["joke"])

        # You can include more complex logic here via a custom function
