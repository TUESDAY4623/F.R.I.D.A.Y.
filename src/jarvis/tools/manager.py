"""Tool Manager stub (Phase 0).

Per Section 4 & 11:
- Tool Manager owns: Validate request -> policy check -> execute -> enforce timeout -> normalize result.
- Tool Manager does NOT own: Defining what a tool can do (that's Tool Registry).
- Receives: Action request.
- Returns: Normalized result or error.
- Called by: Orchestrator.
(To be fully implemented by Adarsh in Phase 1).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from jarvis.tools.contract import ToolResult
from jarvis.tools.registry import ToolRegistry, get_tool_registry


class ToolManager:
    """Tool Manager stub for driving tool execution through the Tool Registry."""

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry or get_tool_registry()

    def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Dispatch action request to registered tool, returning normalized result."""
        if not self.registry.has(tool_name):
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found in registry",
            )
        tool = self.registry.get(tool_name)
        try:
            return tool.execute(arguments)
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Execution failed: {exc}",
            )
