from pathlib import Path

from jarvis.tools import (
    ListDirectoryTool,
    ReadFileTool,
    ToolRegistry,
)
from jarvis.types import PolicyDecision
from jarvis.policy import PolicyEngine


def test_read_file_contract_and_execution(tmp_path: Path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("hello jarvis", encoding="utf-8")

    tool = ReadFileTool()

    assert tool.contract.name == "read_file"
    assert tool.contract.risk_level.value == "low"
    assert tool.contract.reversible is True

    result = tool.execute({"path": str(test_file)})

    assert result.success is True
    assert result.data["content"] == "hello jarvis"


def test_list_directory_contract_and_execution(tmp_path: Path):
    (tmp_path / "one.txt").write_text("one", encoding="utf-8")
    (tmp_path / "two.txt").write_text("two", encoding="utf-8")

    tool = ListDirectoryTool()

    assert tool.contract.name == "list_directory"
    assert tool.contract.risk_level.value == "low"
    assert tool.contract.reversible is True

    result = tool.execute({"path": str(tmp_path)})

    assert result.success is True
    assert "one.txt" in result.data["entries"]
    assert "two.txt" in result.data["entries"]


def test_throwaway_tools_register_and_lookup():
    registry = ToolRegistry()

    registry.register(ReadFileTool())
    registry.register(ListDirectoryTool())

    assert registry.has("read_file")
    assert registry.has("list_directory")

    assert registry.get("read_file").contract.name == "read_file"
    assert registry.get("list_directory").contract.name == "list_directory"


def test_policy_engine_is_phase0_allow_passthrough():
    policy = PolicyEngine()

    decision = policy.check(
        action_name="read_file",
        arguments={"path": "example.txt"},
        contract=ReadFileTool().contract,
    )

    assert decision == PolicyDecision.ALLOW
