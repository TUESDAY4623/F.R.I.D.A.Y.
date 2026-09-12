"""Tool Registry implementation.

Per Section 4 and Section 11:
- Tool Registry owns: per-tool contract (schema, risk level, reversibility, rollback strategy, timeout, idempotency, platform support).
- Tool Registry does NOT own: executing the tool (that's Tool Manager).
- Validates each tool against the contract upon registration.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from jarvis.tools.contract import BaseTool, ToolContract


class ToolRegistry:
    """Central registry of available tools and their contracts."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> ToolContract:
        """Register a tool instance and validate its contract."""
        contract = tool.contract
        if not isinstance(contract, ToolContract):
            raise TypeError(f"Expected ToolContract, got {type(contract)}")

        if contract.name in self._tools:
            raise ValueError(f"Tool with name '{contract.name}' is already registered.")

        self._tools[contract.name] = tool
        return contract

    def unregister(self, name: str) -> None:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> BaseTool:
        """Retrieve a registered tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered in Tool Registry.")
        return self._tools[name]

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def list_tools(self) -> List[ToolContract]:
        """List contracts for all registered tools."""
        return [tool.contract for tool in self._tools.values()]

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()


# Default singleton instance
_default_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the default process-wide Tool Registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry
