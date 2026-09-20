"""Filesystem tool for moving files."""

from __future__ import annotations

import os
import shutil
from typing import Any, Dict

from jarvis.tools.contract import BaseTool, ToolContract, ToolResult
from jarvis.types import RiskLevel


class MoveFileTool(BaseTool):
    """Move a file from one path to another."""

    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="move_file",
            description="Move a file from one path to another",
            input_schema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Path of the file to move",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path for the file",
                    },
                },
                "required": ["source", "destination"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "destination": {"type": "string"},
                },
            },
            risk_level=RiskLevel.MEDIUM,
            reversible=True,
            rollback_strategy="move_back_to_original",
            timeout=5.0,
            idempotency=False,
            required_capabilities=["file_move"],
            platform_support=["windows"],
        )

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Move the requested file."""

        try:
            source = params["source"]
            destination = params["destination"]

            if not os.path.isfile(source):
                return ToolResult(
                    success=False,
                    error=f"Source file does not exist: {source}",
                )

            if os.path.exists(destination):
                return ToolResult(
                    success=False,
                    error=f"Destination already exists: {destination}",
                )

            shutil.move(source, destination)

            return ToolResult(
                success=True,
                data={
                    "source": source,
                    "destination": destination,
                },
            )

        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to move file: {exc}",
            )
