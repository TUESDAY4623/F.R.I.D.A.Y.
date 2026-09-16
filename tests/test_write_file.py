from jarvis.tools.write_file import WriteFileTool


def test_write_file_contract():
    tool = WriteFileTool()
    contract = tool.contract

    assert contract.name == "write_file"
    assert contract.risk_level.value == "medium"
    assert contract.reversible is True
    assert contract.rollback_strategy == "backup_before_overwrite"
    assert contract.timeout == 5.0
    assert contract.idempotency is True
    assert "file_write" in contract.required_capabilities
    assert "windows" in contract.platform_support


def test_write_file_execution(tmp_path):
    tool = WriteFileTool()

    file_path = tmp_path / "test.txt"

    result = tool.execute(
        {
            "path": str(file_path),
            "content": "Hello Jarvis",
        }
    )

    assert result.success is True
    assert file_path.read_text(encoding="utf-8") == "Hello Jarvis"
    assert result.data["path"] == str(file_path)
    assert result.data["bytes_written"] == len("Hello Jarvis".encode("utf-8"))


def test_write_file_overwrites_existing_file(tmp_path):
    tool = WriteFileTool()

    file_path = tmp_path / "test.txt"
    file_path.write_text("old content", encoding="utf-8")

    result = tool.execute(
        {
            "path": str(file_path),
            "content": "new content",
        }
    )

    assert result.success is True
    assert file_path.read_text(encoding="utf-8") == "new content"
