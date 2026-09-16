import os

from jarvis.tools.create_directory import CreateDirectoryTool
from jarvis.types import RiskLevel


def test_create_directory_contract():
    tool = CreateDirectoryTool()
    contract = tool.contract

    assert contract.name == "create_directory"
    assert contract.risk_level == RiskLevel.MEDIUM
    assert contract.reversible is True
    assert contract.rollback_strategy == "remove_created_directory"
    assert contract.timeout == 5.0
    assert contract.idempotency is False
    assert contract.required_capabilities == ["directory_write"]
    assert contract.platform_support == ["windows"]


def test_create_directory_success(tmp_path):
    tool = CreateDirectoryTool()
    directory = tmp_path / "new_directory"

    result = tool.execute({"path": str(directory)})

    assert result.success is True
    assert result.data["path"] == str(directory)
    assert directory.is_dir()


def test_create_directory_existing_path_fails(tmp_path):
    tool = CreateDirectoryTool()
    directory = tmp_path / "existing_directory"
    directory.mkdir()

    result = tool.execute({"path": str(directory)})

    assert result.success is False
    assert "Failed to create directory" in result.error


def test_create_directory_missing_path_fails():
    tool = CreateDirectoryTool()

    result = tool.execute({})

    assert result.success is False
    assert "Failed to create directory" in result.error


def test_create_directory_wrong_path_type_fails(tmp_path):
    tool = CreateDirectoryTool()

    result = tool.execute({"path": 123})

    assert result.success is False
    assert "Failed to create directory" in result.error
