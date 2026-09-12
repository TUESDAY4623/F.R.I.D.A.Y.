"""Tests for the Tool Registry contract per Section 11 and Section 7."""

import pytest
from jarvis.tools import BaseTool, ToolContract, ToolRegistry, ToolResult
from jarvis.types import RiskLevel


class MockValidTool(BaseTool):
    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="mock_file_read",
            description="Reads file contents from disk",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            output_schema={
                "type": "object",
                "properties": {"content": {"type": "string"}},
            },
            risk_level=RiskLevel.LOW,
            reversible=True,
            rollback_strategy="none_needed",
            timeout=10.0,
            idempotency=True,
            required_capabilities=["file_read"],
            platform_support=["windows"],
        )

    def execute(self, params: dict) -> ToolResult:
        return ToolResult(success=True, data={"content": "file contents"})


def test_tool_contract_all_fields_present():
    """Verify all 11 required contract fields from Section 11 are defined and accessible."""
    tool = MockValidTool()
    contract = tool.contract

    assert contract.name == "mock_file_read"
    assert contract.description == "Reads file contents from disk"
    assert "properties" in contract.input_schema
    assert "properties" in contract.output_schema
    assert contract.risk_level == RiskLevel.LOW
    assert contract.reversible is True
    assert contract.rollback_strategy == "none_needed"
    assert contract.timeout == 10.0
    assert contract.idempotency is True
    assert "file_read" in contract.required_capabilities
    assert "windows" in contract.platform_support


def test_tool_registry_registration_and_lookup():
    """Verify registration, lookup, listing, and execution via Tool Registry."""
    registry = ToolRegistry()
    tool = MockValidTool()

    contract = registry.register(tool)
    assert contract.name == "mock_file_read"
    assert registry.has("mock_file_read")
    assert registry.get("mock_file_read") == tool
    assert len(registry.list_tools()) == 1

    # Duplicate registration should raise ValueError
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


def test_medium_risk_requires_reversibility_and_rollback():
    """Section 7 & 11: MEDIUM risk requires reversible: True and rollback_strategy."""
    # Medium risk without reversibility must fail
    with pytest.raises(ValueError, match="MEDIUM risk tools must declare reversible: True"):
        ToolContract(
            name="invalid_medium_tool",
            description="Tries to be medium without reversibility",
            input_schema={},
            output_schema={},
            risk_level=RiskLevel.MEDIUM,
            reversible=False,
            timeout=5.0,
            idempotency=False,
            required_capabilities=[],
            platform_support=["windows"],
        )

    # Medium risk without rollback strategy must fail
    with pytest.raises(ValueError, match="declare a rollback_strategy"):
        ToolContract(
            name="invalid_medium_tool_no_strategy",
            description="Tries to be medium without rollback strategy",
            input_schema={},
            output_schema={},
            risk_level=RiskLevel.MEDIUM,
            reversible=True,
            rollback_strategy=None,
            timeout=5.0,
            idempotency=False,
            required_capabilities=[],
            platform_support=["windows"],
        )


def test_irreversible_action_must_be_high_risk():
    """Section 7: Anything declared reversible: false must be designated HIGH risk."""
    with pytest.raises(ValueError, match="Irreversible tools.*must be designated HIGH risk"):
        ToolContract(
            name="invalid_low_irreversible",
            description="Irreversible tool trying to declare low risk",
            input_schema={},
            output_schema={},
            risk_level=RiskLevel.LOW,
            reversible=False,
            timeout=5.0,
            idempotency=False,
            required_capabilities=[],
            platform_support=["windows"],
        )
