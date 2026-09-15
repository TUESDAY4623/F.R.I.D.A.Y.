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

    return application


def test_main_window_initializes(app):
    orchestrator = Mock()
    logger = Mock()

    window = MainWindow(
        orchestrator=orchestrator,
        logger=logger,
    )

    assert window.input_box is not None
    assert window.send_button is not None
    assert window.response_box is not None
    assert window.log_box is not None


def test_empty_request_is_ignored(app):
    orchestrator = Mock()
    logger = Mock()

    window = MainWindow(
        orchestrator=orchestrator,
        logger=logger,
    )

    window.input_box.setPlainText("")
    window.submit_request()

    orchestrator.execute_task.assert_not_called()


def test_request_is_sent_to_orchestrator(app):
    orchestrator = Mock()

    orchestrator.execute_task.return_value = {
        "task_id": "task_test",
        "success": True,
        "status": "COMPLETED",
        "executed_steps": [],
        "steps_count": 0,
    }

    logger = Mock()

    window = MainWindow(
        orchestrator=orchestrator,
        logger=logger,
    )

    window.input_box.setPlainText("Hello Jarvis")
    window.submit_request()

    orchestrator.execute_task.assert_called_once_with(
        "Hello Jarvis"
    )