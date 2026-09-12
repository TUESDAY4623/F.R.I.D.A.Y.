"""Tool Registry contract definition.

Per Section 11 (Tool Registry Contract):
Every tool declares:
- name (str)
- description (str)
- input_schema (dict)
- output_schema (dict)
- risk_level (RiskLevel: low / medium / high)
- reversible (bool)
- rollback_strategy (Optional[str])
- timeout (float)
- idempotency (bool)
- required_capabilities (list[str])
- platform_support (list[str])

Also establishes BaseTool and ToolResult contracts before any real tools are built against it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from jarvis.types import RiskLevel


class ToolContract(BaseModel):
    """Immutable specification declaring a tool's capability and safety profile.

    Per Section 11 and Section 7:
    - Reversibility and risk are tool-level facts declared once in the Tool Registry.
    - If a tool does not declare reversibility, it cannot be MEDIUM risk regardless
      of what it does (it must be HIGH risk).
    - Destructive or irreversible actions require reversible: false and HIGH risk.
    """

    name: str = Field(..., min_length=1, description="Unique identifier for the tool")
    description: str = Field(..., min_length=1, description="Human- and LLM-readable summary of capability")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema defining valid arguments")
    output_schema: Dict[str, Any] = Field(..., description="JSON Schema defining return data")
    risk_level: RiskLevel = Field(..., description="Risk tier: low, medium, or high")
    reversible: bool = Field(..., description="Whether actions performed can be reversed/undone")
    rollback_strategy: Optional[str] = Field(
        None,
        description="Mechanism used to reverse action (e.g., 'recycle_bin', 'backup_before_overwrite')",
    )
    timeout: float = Field(..., gt=0, description="Per-execution timeout limit in seconds")
    idempotency: bool = Field(..., description="Whether executing repeatedly with identical arguments is safe")
    required_capabilities: List[str] = Field(
        default_factory=list,
        description="System or runtime capabilities required (e.g. ['file_read', 'network'])",
    )
    platform_support: List[str] = Field(
        default_factory=lambda: ["windows"],
        min_length=1,
        description="Target platforms supported (e.g. ['windows'])",
    )

    @model_validator(mode="after")
    def validate_risk_and_reversibility(self) -> ToolContract:
        # Per Section 7: "If a tool doesn't declare reversibility, it cannot be MEDIUM regardless of what it does."
        if self.risk_level == RiskLevel.MEDIUM:
            if not self.reversible:
                raise ValueError(
                    f"Tool '{self.name}': MEDIUM risk tools must declare reversible: True "
                    f"and specify a rollback_strategy. Irreversible tools must be HIGH risk."
                )
            if not self.rollback_strategy:
                raise ValueError(
                    f"Tool '{self.name}': MEDIUM risk tools must declare a rollback_strategy."
                )

        # Per Section 7: "anything the Tool Registry declares reversible: false ... Always routed through Approval Manager"
        if not self.reversible and self.risk_level != RiskLevel.HIGH:
            raise ValueError(
                f"Tool '{self.name}': Irreversible tools (reversible: False) must be designated HIGH risk."
            )

        return self


class ToolResult(BaseModel):
    """Normalized result returned by tool execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """Base class for all tools registered in the Tool Registry."""

    @property
    @abstractmethod
    def contract(self) -> ToolContract:
        """The tool's immutable contract specification."""
        pass

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute the tool with validated arguments."""
        pass
