import pytest
from jarvis.tools.move_file import MoveFileTool
from jarvis.types import RiskLevel


def test_move_file_contract():
    tool = MoveFileTool()
    contract = tool.contract

    assert contract.name == "move_file"
    assert contract.risk_level == RiskLevel.MEDIUM
    assert contract.reversible is True
    assert contract.rollback_strategy == "move_back_to_original"
    assert contract.timeout == 5.0
    assert contract.idempotency is False
    assert contract.required_capabilities == ["file_move"]
    assert contract.platform_support == ["windows"]


def test_move_file_moves_file(tmp_path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "destination.txt"

    source.write_text("Hello Jarvis", encoding="utf-8")

    tool = MoveFileTool()
    result = tool.execute(
        {
            "source": str(source),
            "destination": str(destination),
        }
    )

    assert result.success is True
    assert not source.exists()
    assert destination.exists()
    assert destination.read_text(encoding="utf-8") == "Hello Jarvis"


def test_move_file_fails_when_source_missing(tmp_path):
    source = tmp_path / "missing.txt"
    destination = tmp_path / "destination.txt"

    tool = MoveFileTool()
    result = tool.execute(
        {
            "source": str(source),
            "destination": str(destination),
        }
    )

    assert result.success is False
    assert "does not exist" in result.error


def test_move_file_fails_when_destination_exists(tmp_path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "destination.txt"

    source.write_text("source", encoding="utf-8")
    destination.write_text("existing", encoding="utf-8")

    tool = MoveFileTool()
    result = tool.execute(
        {
            "source": str(source),
            "destination": str(destination),
        }
    )

    assert result.success is False
    assert "already exists" in result.error


def test_move_file_missing_arguments_fails():
    tool = MoveFileTool()
    result = tool.execute({})
    assert result.success is False
    assert "Failed to move file" in result.error
