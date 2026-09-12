from __future__ import annotations

from typing import Any, Dict

from jarvis.tools.contract import BaseTool, ToolContract, ToolResult
from jarvis.types import RiskLevel


class ListDirectoryTool(BaseTool):
    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="list_directory",
            description="List entries in a directory.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the directory to list.",
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of entries in the directory.",
                    }
                },
                "required": ["entries"],
            },
            risk_level=RiskLevel.LOW,
            reversible=True,
            rollback_strategy=None,
            timeout=5.0,
            idempotency=True,
            required_capabilities=["directory_read"],
            platform_support=["windows"],
        )

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = params.get("path")

        if not isinstance(path, str) or not path:
            return ToolResult(
                success=False,
                error="Missing required parameter: path",
            )

        try:
            import os

            entries = os.listdir(path)

            return ToolResult(
                success=True,
                data={"entries": entries},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to list directory: {exc}",
            )
