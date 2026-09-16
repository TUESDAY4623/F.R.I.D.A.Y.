import sys

import pytest

if sys.platform != "win32":
    pytest.skip(
        "Jarvis UI tests require Windows",
        allow_module_level=True,
    )

from PySide6.QtWidgets import QApplication
from unittest.mock import Mock

from jarvis.ui.main_window import MainWindow


@pytest.fixture
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application

    for widget in application.topLevelWidgets():
        widget.close()
        widget.deleteLater()

    application.processEvents()


@pytest.fixture
def window(app):
    orchestrator = Mock()
    logger = Mock()

    main_window = MainWindow(
        orchestrator=orchestrator,
        logger=logger,
    )

    yield main_window, orchestrator, logger

    main_window.close()
    main_window.deleteLater()
    app.processEvents()


def test_main_window_initializes(window):
    window, _, _ = window

    assert window.input_box is not None
    assert window.send_button is not None
    assert window.response_box is not None
    assert window.log_box is not None


def test_empty_request_is_ignored(window):
    window, orchestrator, _ = window

    window.input_box.setPlainText("")
    window.submit_request()

    orchestrator.execute_task.assert_not_called()


def test_request_is_sent_to_orchestrator(window):
    window, orchestrator, _ = window

    orchestrator.execute_task.return_value = {
        "task_id": "task_test",
        "success": True,
        "status": "COMPLETED",
        "executed_steps": [],
        "steps_count": 0,
    }

    window.input_box.setPlainText("Hello Jarvis")
    window.submit_request()

    orchestrator.execute_task.assert_called_once_with(
        "Hello Jarvis"
    )


def test_task_state_badge_updates(window):
    window, _, _ = window

    assert window.status_badge.text() == "IDLE"

    window._update_task_state("EXECUTING")
    assert window.status_badge.text() == "EXECUTING"

    window._update_task_state("COMPLETED")
    assert window.status_badge.text() == "COMPLETED"


def test_tool_call_tree_events(window):
    window, _, _ = window

    # Dispatch a tool start event
    start_event = {
        "type": "tool.started",
        "step_name": "6. Dispatch action",
        "message": "Dispatching read_file",
        "payload": {
            "tool_name": "read_file",
            "arguments": {"path": "test.txt"},
        },
    }

    window._handle_tool_event(start_event)

    assert window.tool_call_tree.topLevelItemCount() == 1
    item = window.tool_call_tree.topLevelItem(0)
    assert "read_file" in item.text(0)
    assert item.text(1) == "RUNNING"

    # Dispatch tool completion
    complete_event = {
        "type": "tool.completed",
        "step_name": "6. Dispatch action",
        "message": "Tool execution completed",
        "payload": {
            "tool_name": "read_file",
            "result": {"content": "sample text"},
        },
    }

    window._handle_tool_event(complete_event)
    assert item.text(1) == "SUCCESS"