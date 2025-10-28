from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from elysia.api.dependencies.common import get_user_manager
from elysia.api.services.user import UserManager
from elysia.api.core.log import logger
from elysia.tree.tree import Tree
from elysia.api.api_types import (
    AddToolToTreeData,
    RemoveToolFromTreeData,
    AddBranchToTreeData,
    RemoveBranchFromTreeData,
)
from elysia.api.services.tree import TreeManager
from elysia.util.tool_discovery import discover_tools_from_module, get_tool_metadata

router = APIRouter()


@router.get("/available")
async def get_available_tools():
    headers = {"Cache-Control": "no-cache"}

    try:
        return JSONResponse(
            content={"tools": get_tool_metadata(), "error": ""},
            status_code=200,
            headers=headers,
        )
    except Exception as e:
        logger.error(f"Error getting available tools: {str(e)}")
        return JSONResponse(
            content={"tools": {}, "error": str(e)},
            status_code=500,
            headers=headers,
        )


@router.post("/{user_id}/add")
async def add_tool_to_tree(
    user_id: str,
    data: AddToolToTreeData,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        # get tool class
        tool_class = discover_tools_from_module()[data.tool_name]
        user = await user_manager.get_user_local(user_id)
        tree_manager: TreeManager = user["tree_manager"]

        # get tree and add tool
        for conversation_id in tree_manager.trees:
            tree: Tree = tree_manager.get_tree(conversation_id)
            tree.add_tool(tool_class, data.branch_id, from_tool_ids=data.from_tool_ids)

        # all trees should look the same, so return the most recent one
        return JSONResponse(content={"tree": tree.tree, "error": ""}, status_code=200)

    except Exception as e:
        logger.error(f"Error adding tool to tree: {str(e)}")
        return JSONResponse(content={"tree": {}, "error": str(e)}, status_code=500)


@router.post("/{user_id}/remove")
async def remove_tool_from_tree(
    user_id: str,
    data: RemoveToolFromTreeData,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        # get tool class
        tool_class = discover_tools_from_module()[data.tool_name]

        # get tree and remove tool
        user = await user_manager.get_user_local(user_id)
        tree_manager: TreeManager = user["tree_manager"]
        for conversation_id in tree_manager.trees:
            tree: Tree = tree_manager.get_tree(conversation_id)
            tree.remove_tool(
                tool_class.get_metadata()["name"],  # type: ignore
                data.branch_id,
                from_tool_ids=data.from_tool_ids,
            )

        return JSONResponse(content={"tree": tree.tree, "error": ""}, status_code=200)
    except Exception as e:
        logger.error(f"Error removing tool from tree: {str(e)}")
        return JSONResponse(content={"tree": {}, "error": str(e)}, status_code=500)


@router.post("/{user_id}/add_branch")
async def add_branch_to_tree(
    user_id: str,
    data: AddBranchToTreeData,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        # get tree and add branch
        user = await user_manager.get_user_local(user_id)
        tree_manager: TreeManager = user["tree_manager"]
        for conversation_id in tree_manager.trees:
            tree: Tree = tree_manager.get_tree(conversation_id)
            tree.add_branch(
                branch_id=data.id,
                instruction=data.instruction,
                description=data.description,
                root=data.root,
                from_branch_id=data.from_branch_id,
                from_tool_ids=data.from_tool_ids,
                status=data.status,
            )

        return JSONResponse(content={"tree": tree.tree, "error": ""}, status_code=200)
    except Exception as e:
        logger.error(f"Error adding branch to tree: {str(e)}")
        return JSONResponse(content={"tree": {}, "error": str(e)}, status_code=500)


@router.post("/{user_id}/remove_branch")
async def remove_branch_from_tree(
    user_id: str,
    data: RemoveBranchFromTreeData,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        # get tree and remove branch
        user = await user_manager.get_user_local(user_id)
        tree_manager: TreeManager = user["tree_manager"]
        for conversation_id in tree_manager.trees:
            tree: Tree = tree_manager.get_tree(conversation_id)
            tree.remove_branch(data.id)

        return JSONResponse(content={"tree": tree.tree, "error": ""}, status_code=200)
    except Exception as e:
        logger.error(f"Error removing branch from tree: {str(e)}")
        return JSONResponse(content={"tree": {}, "error": str(e)}, status_code=500)
