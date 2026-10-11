"""No-op tool for Phase 0 compatibility and general fallback steps."""

from __future__ import annotations

from typing import Any, Dict

from jarvis.tools.contract import BaseTool, ToolContract, ToolResult
from jarvis.types import RiskLevel


class NoopTool(BaseTool):
    """No-operation tool that safely completes without side effects."""

    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="noop_tool",
            description="No-operation fallback tool",
            input_schema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                },
            },
            risk_level=RiskLevel.LOW,
            reversible=True,
            rollback_strategy=None,
            timeout=5.0,
            idempotency=True,
            required_capabilities=[],
            platform_support=["windows"],
        )

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        return ToolResult(
            success=True,
            data={"status": "noop_completed", "params": params},
        )
