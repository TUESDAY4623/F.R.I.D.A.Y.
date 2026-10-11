"""Filesystem tool for creating directories."""

from __future__ import annotations

import os
from typing import Any, Dict

from jarvis.tools.contract import BaseTool, ToolContract, ToolResult
from jarvis.types import RiskLevel


class CreateDirectoryTool(BaseTool):
    """Create a directory without modifying an existing directory."""

    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="create_directory",
            description="Create a new directory",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                },
                "required": ["path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                },
            },
            risk_level=RiskLevel.MEDIUM,
            reversible=True,
            rollback_strategy="remove_created_directory",
            timeout=5.0,
            idempotency=False,
            required_capabilities=["directory_write"],
            platform_support=["windows"],
        )

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Create the requested directory."""

        try:
            path = params["path"]
            os.makedirs(path, exist_ok=False)

            return ToolResult(
                success=True,
                data={
                    "path": path,
                },
            )

        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to create directory: {exc}",
            )
