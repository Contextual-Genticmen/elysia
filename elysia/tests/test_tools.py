import os
import unittest
import asyncio
from dspy import LM
from elysia.objects import Result
from copy import deepcopy
from elysia import Tool
from elysia.tree.objects import TreeData
from elysia.config import Settings, configure
from elysia.tree.tree import Tree
from elysia.tools.text.text import TextResponse

try:
    # get_ipython
    os.chdir("../..")
except NameError:
    pass

from elysia.util.client import ClientManager
from elysia.tests.dummy_adapter import dummy_adapter

configure(logging_level="CRITICAL")


class RunIfTrueFalseTool(Tool):
    def __init__(self, **kwargs):
        super().__init__(
            name="run_if_true_false_tool",
            description="Always returns False",
            rule=True,
        )

    async def is_tool_available(self, tree_data, base_lm, complex_lm, client_manager):
        return False

    async def run_if_true(
        self,
        tree_data: dict,
        base_lm: LM,
        complex_lm: LM,
        client_manager: ClientManager,
    ):
        return False

    async def __call__(
        self,
        tree_data: TreeData,
        inputs: dict,
        base_lm: LM,
        complex_lm: LM,
        client_manager: ClientManager,
        **kwargs,
    ):

        tree_data.environment.add(
            Result(
                objects=[{"message": "Rule tool called!!!"}],
                type="text",
                name="rule_tool",
            ),
            "rule_tool",
        )
        yield False


class RunIfTrueTrueTool(Tool):
    def __init__(self, **kwargs):
        super().__init__(
            name="run_if_true_true_tool",
            description="Always returns True",
            rule=True,
        )

    async def is_tool_available(self, tree_data, base_lm, complex_lm, client_manager):
        return False

    async def run_if_true(
        self,
        tree_data: TreeData,
        base_lm: LM,
        complex_lm: LM,
        client_manager: ClientManager,
    ):
        return True

    async def __call__(
        self,
        tree_data: TreeData,
        inputs: dict,
        base_lm: LM,
        complex_lm: LM,
        client_manager: ClientManager,
        **kwargs,
    ):

        tree_data.environment.add(
            Result(
                objects=[{"message": "Rule tool called!!!"}],
                type="text",
                name="rule_tool",
            ),
            "rule_tool",
        )
        yield True


class ToolNotAvailable(Tool):
    def __init__(self, **kwargs):
        super().__init__(
            name="always_pick_this_tool",
            description="No matter what, always pick this tool, and END the conversation.",
            rule=True,
            end=True,
        )

    async def is_tool_available(self, tree_data, base_lm, complex_lm, client_manager):
        return False

    async def __call__(
        self,
        tree_data: TreeData,
        inputs: dict,
        base_lm: LM,
        complex_lm: LM,
        client_manager: ClientManager,
        **kwargs,
    ):
        yield True


class ToolAvailable(Tool):
    def __init__(self, **kwargs):
        super().__init__(
            name="always_pick_this_tool",
            description="No matter what, always pick this tool, and END the conversation.",
            rule=True,
            end=True,
        )

    async def is_tool_available(self, tree_data, base_lm, complex_lm, client_manager):
        return True

    async def __call__(
        self,
        tree_data: TreeData,
        inputs: dict,
        base_lm: LM,
        complex_lm: LM,
        client_manager: ClientManager,
        **kwargs,
    ):
        yield True


class IncorrectToolInitialisation_kwargs_init(Tool):
    def __init__(self):
        super().__init__(
            name="incorrect_tool_initialisation",
            description="This tool should not be initialised",
        )


class IncorrectToolInitialisation_kwargs_call(Tool):
    def __init__(self):
        super().__init__(
            name="incorrect_tool_initialisation",
            description="This tool should not be initialised",
        )

    async def __call__(self, tree_data, inputs, base_lm, complex_lm, client_manager):
        yield True


class IncorrectToolInitialisation_call_non_async(Tool):
    def __init__(self):
        super().__init__(
            name="incorrect_tool_initialisation",
            description="This tool should not be initialised",
        )

    def __call__(self, tree_data, inputs, base_lm, complex_lm, client_manager):
        return True


class IncorrectToolInitialisation_call_non_async_generator(Tool):
    def __init__(self):
        super().__init__(
            name="incorrect_tool_initialisation",
            description="This tool should not be initialised",
        )

    async def __call__(self, tree_data, inputs, base_lm, complex_lm, client_manager):
        return True


class TestTools(unittest.TestCase):

    base_tree = Tree(
        debug=True,
        branch_initialisation="empty",
        settings=Settings.from_default(),
    )

    def get_event_loop(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop

    async def run_tree(
        self,
        user_prompt: str,
        collection_names: list[str],
        tools: list[Tool],
        remove_tools: bool = False,
    ):
        tree = deepcopy(self.base_tree)

        if not remove_tools:
            tree.add_tool(TextResponse)

        for tool in tools:
            tree.add_tool(tool)

        async for result in tree.async_run(
            user_prompt,
            collection_names=collection_names,
        ):
            pass
        return tree

    def test_run_if_true_false_tool(self):

        loop = self.get_event_loop()

        tree = loop.run_until_complete(self.run_tree("Hello", [], [RunIfTrueFalseTool]))

        self.assertNotIn("rule_tool", tree.tree_data.environment.environment)

    def test_run_if_true_true_tool(self):

        loop = self.get_event_loop()

        tree = loop.run_until_complete(self.run_tree("Hello", [], [RunIfTrueTrueTool]))

        self.assertIn("rule_tool", tree.tree_data.environment.environment)

    def test_tool_not_available(self):

        loop = self.get_event_loop()

        with self.assertRaises(RuntimeError):  # should have no tools available
            loop.run_until_complete(
                self.run_tree("Hello", [], [ToolNotAvailable], remove_tools=True)
            )

    def test_tool_available(self):

        loop = self.get_event_loop()

        tree = loop.run_until_complete(
            self.run_tree("Hello", [], [ToolAvailable], remove_tools=True)
        )

        self.assertIn("always_pick_this_tool", tree.decision_history)

    def test_incorrect_tool_initialisation(self):
        with self.assertRaises(TypeError):
            tree = deepcopy(self.base_tree)
            tree.add_tool(IncorrectToolInitialisation_kwargs_init)

        with self.assertRaises(TypeError):
            tree = deepcopy(self.base_tree)
            tree.add_tool(IncorrectToolInitialisation_kwargs_call)

        with self.assertRaises(TypeError):
            tree = deepcopy(self.base_tree)
            tree.add_tool(IncorrectToolInitialisation_call_non_async)

        with self.assertRaises(TypeError):
            tree = deepcopy(self.base_tree)
            tree.add_tool(IncorrectToolInitialisation_call_non_async_generator)


if __name__ == "__main__":
    with dummy_adapter():
        TestTools().test_tool_available()
