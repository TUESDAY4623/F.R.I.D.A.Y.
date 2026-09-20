"""Application Bootstrap module for Jarvis Desktop Agent.

Follows Section 4 and Phase 1 architecture:
Application Bootstrap -> Tool Registration -> Tool Registry -> Tool Manager
"""

from __future__ import annotations

from typing import Optional

from jarvis.tools.create_directory import CreateDirectoryTool
from jarvis.tools.list_directory import ListDirectoryTool
from jarvis.tools.move_file import MoveFileTool
from jarvis.tools.noop import NoopTool
from jarvis.tools.read_file import ReadFileTool
from jarvis.tools.registry import ToolRegistry, get_tool_registry
from jarvis.tools.write_file import WriteFileTool


def register_default_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    """Register all standard Phase 1 filesystem tools and fallback noop tool."""
    target_registry = registry or get_tool_registry()

    default_tools = [
        ReadFileTool(),
        WriteFileTool(),
        ListDirectoryTool(),
        CreateDirectoryTool(),
        MoveFileTool(),
        NoopTool(),
    ]

    for tool in default_tools:
        if not target_registry.has(tool.contract.name):
            target_registry.register(tool)

    return target_registry


def bootstrap_agent(registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    """Bootstrap application-level services and tool registries."""
    return register_default_tools(registry)
