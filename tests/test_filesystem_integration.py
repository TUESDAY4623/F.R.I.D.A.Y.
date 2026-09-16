from pathlib import Path

from jarvis.tools.create_directory import CreateDirectoryTool
from jarvis.tools.list_directory import ListDirectoryTool
from jarvis.tools.manager import ToolManager
from jarvis.tools.read_file import ReadFileTool
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.write_file import WriteFileTool
from jarvis.types import PolicyDecision


class AllowPolicy:
    def check(self, action_name, arguments, contract=None):
        return PolicyDecision.ALLOW


def make_manager(*tools):
    registry = ToolRegistry()

    for tool in tools:
        registry.register(tool)

    return ToolManager(
        registry=registry,
        policy_engine=AllowPolicy(),
    )


def test_read_file_through_tool_manager(tmp_path):
    file_path = tmp_path / "read.txt"
    file_path.write_text("Hello Jarvis", encoding="utf-8")

    manager = make_manager(ReadFileTool())

    result = manager.dispatch(
        "read_file",
        {"path": str(file_path)},
    )

    assert result.success is True
    assert result.data == {"content": "Hello Jarvis"}


def test_list_directory_through_tool_manager(tmp_path):
    (tmp_path / "one.txt").write_text("one", encoding="utf-8")
    (tmp_path / "two.txt").write_text("two", encoding="utf-8")

    manager = make_manager(ListDirectoryTool())

    result = manager.dispatch(
        "list_directory",
        {"path": str(tmp_path)},
    )

    assert result.success is True
    assert "one.txt" in result.data["entries"]
    assert "two.txt" in result.data["entries"]


def test_write_file_through_tool_manager(tmp_path):
    file_path = tmp_path / "write.txt"

    manager = make_manager(WriteFileTool())

    result = manager.dispatch(
        "write_file",
        {
            "path": str(file_path),
            "content": "Written by Jarvis",
        },
    )

    assert result.success is True
    assert file_path.read_text(encoding="utf-8") == "Written by Jarvis"
    assert result.metadata["policy_decision"] == "allow"


def test_create_directory_through_tool_manager(tmp_path):
    directory = tmp_path / "new_directory"

    manager = make_manager(CreateDirectoryTool())

    result = manager.dispatch(
        "create_directory",
        {"path": str(directory)},
    )

    assert result.success is True
    assert directory.is_dir()
    assert result.metadata["policy_decision"] == "allow"


def test_filesystem_tools_are_registered():
    tools = [
        ReadFileTool(),
        ListDirectoryTool(),
        WriteFileTool(),
        CreateDirectoryTool(),
    ]

    manager = make_manager(*tools)

    assert manager.registry.has("read_file")
    assert manager.registry.has("list_directory")
    assert manager.registry.has("write_file")
    assert manager.registry.has("create_directory")
