"""Filesystem tool for creating or overwriting text files."""

from __future__ import annotations

from typing import Dict, Any

from jarvis.tools.contract import BaseTool, ToolContract, ToolResult
from jarvis.types import RiskLevel


class WriteFileTool(BaseTool):
    """Create or overwrite a UTF-8 text file."""

    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="write_file",
            description="Create or overwrite file contents",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path of the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write",
                    },
                },
                "required": ["path", "content"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "bytes_written": {"type": "integer"},
                },
            },
            risk_level=RiskLevel.MEDIUM,
            reversible=True,
            rollback_strategy="backup_before_overwrite",
            timeout=5.0,
            idempotency=True,
            required_capabilities=["file_write"],
            platform_support=["windows"],
        )

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Write UTF-8 text to the requested file."""

        try:
            path = params["path"]
            content = params["content"]

            with open(path, "w", encoding="utf-8") as file:
                file.write(content)

            return ToolResult(
                success=True,
                data={
                    "path": path,
                    "bytes_written": len(content.encode("utf-8")),
                },
            )

        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to write file: {exc}",
            )
