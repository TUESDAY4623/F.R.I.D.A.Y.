
from __future__ import annotations

from typing import Any, Dict

from jarvis.tools.contract import BaseTool, ToolContract, ToolResult
from jarvis.types import RiskLevel


class ReadFileTool(BaseTool):
    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="read_file",
            description="Read the text contents of a file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read.",
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Text contents of the file.",
                    }
                },
                "required": ["content"],
            },
            risk_level=RiskLevel.LOW,
            reversible=True,
            rollback_strategy=None,
            timeout=5.0,
            idempotency=True,
            required_capabilities=["file_read"],
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
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()

            return ToolResult(
                success=True,
                data={"content": content},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to read file: {exc}",
            )
