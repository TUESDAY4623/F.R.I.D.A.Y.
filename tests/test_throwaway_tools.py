from pathlib import Path

from jarvis.policy import PolicyEngine
from jarvis.types import PolicyDecision, RiskLevel
from jarvis.tools import ToolRegistry
from jarvis.tools.read_file import ReadFileTool
from jarvis.tools.list_directory import ListDirectoryTool


def test_read_file_contract_and_execution(tmp_path: Path):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("hello jarvis", encoding="utf-8")

    tool = ReadFileTool()

    assert tool.contract.name == "read_file"
    assert tool.contract.risk_level == RiskLevel.LOW
    assert tool.contract.reversible is True

    result = tool.execute({"path": str(test_file)})

    assert result.success is True
    assert result.data["content"] == "hello jarvis"


def test_list_directory_contract_and_execution(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")

    tool = ListDirectoryTool()

    assert tool.contract.name == "list_directory"
    assert tool.contract.risk_level == RiskLevel.LOW
    assert tool.contract.reversible is True

    result = tool.execute({"path": str(tmp_path)})

    assert result.success is True
    assert set(result.data["entries"]) == {"a.txt", "b.txt"}


def test_throwaway_tools_register_and_lookup():
    registry = ToolRegistry()

    read_tool = ReadFileTool()
    list_tool = ListDirectoryTool()

    registry.register(read_tool)
    registry.register(list_tool)

    assert registry.has("read_file")
    assert registry.has("list_directory")
    assert registry.get("read_file") is read_tool
    assert registry.get("list_directory") is list_tool






def test_policy_engine_allows_action():
    policy = PolicyEngine()
    tool = ReadFileTool()

    decision = policy.check(
        action_name="read_file",
        arguments={"path": "example.txt"},
        contract=tool.contract,
    )

    assert decision == PolicyDecision.ALLOW
