"""Phase 2 UI Unit and Integration Tests.

Validates:
- ApprovalDialog modal rendering and decision returns (APPROVE, DENY, CANCEL).
- MainWindow approval bridge integration with ApprovalManager.
- Interactive task controls (Pause, Resume, Cancel).
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from jarvis.approval import ApprovalManager, ApprovalRequest
from jarvis.types import ApprovalDecision, TaskLifecycle
from jarvis.ui.approval_dialog import ApprovalDialog
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
    approval_mgr = ApprovalManager()

    state_mgr = Mock()
    orchestrator.state_manager = state_mgr

    main_window = MainWindow(
        orchestrator=orchestrator,
        logger=logger,
        approval_manager=approval_mgr,
    )

    yield main_window, orchestrator, logger, approval_mgr, state_mgr

    main_window.close()
    main_window.deleteLater()
    app.processEvents()


def test_approval_dialog_initialization(app):
    req = ApprovalRequest(
        action="move_file",
        target="C:/important.txt",
        consequences="File will be moved to archive",
        reversible=True,
        reason="Policy confirmation required",
    )

    dialog = ApprovalDialog(req)

    assert dialog.request.action == "move_file"
    assert dialog.request.target == "C:/important.txt"
    assert dialog.btn_approve is not None
    assert dialog.btn_deny is not None
    assert dialog.btn_cancel is not None

    dialog.close()
    dialog.deleteLater()


def test_approval_dialog_approve_decision(app):
    req = ApprovalRequest(
        action="move_file",
        target="C:/important.txt",
        consequences="File will be moved",
        reversible=True,
        reason="Policy trigger",
    )

    dialog = ApprovalDialog(req)
    dialog._on_approve()

    assert dialog.get_decision() == ApprovalDecision.APPROVE

    dialog.close()
    dialog.deleteLater()


def test_approval_dialog_deny_decision(app):
    req = ApprovalRequest(
        action="delete_file",
        target="C:/important.txt",
        consequences="Permanent deletion",
        reversible=False,
        reason="HIGH risk policy",
    )

    dialog = ApprovalDialog(req)
    dialog._on_deny()

    assert dialog.get_decision() == ApprovalDecision.DENY

    dialog.close()
    dialog.deleteLater()


def test_approval_dialog_cancel_decision(app):
    req = ApprovalRequest(
        action="delete_file",
        target="C:/important.txt",
        consequences="Permanent deletion",
        reversible=False,
        reason="HIGH risk policy",
    )

    dialog = ApprovalDialog(req)
    dialog._on_cancel()

    assert dialog.get_decision() == ApprovalDecision.CANCEL

    dialog.close()
    dialog.deleteLater()


def test_main_window_approval_handler_integration(window):
    main_window, _, _, approval_mgr, _ = window

    req = ApprovalRequest(
        action="move_file",
        target="C:/test.txt",
        consequences="Move file",
        reversible=True,
        reason="Testing UI handler",
    )

    with patch("jarvis.ui.approval_dialog.ApprovalDialog.exec") as mock_exec:
        with patch("jarvis.ui.approval_dialog.ApprovalDialog.get_decision", return_value=ApprovalDecision.APPROVE):
            decision = approval_mgr.request_approval(req)
            assert decision == ApprovalDecision.APPROVE
            assert mock_exec.called


def test_task_control_buttons_pause_resume_cancel(window):
    main_window, _, _, _, state_mgr = window

    main_window._current_task_id = "task_ui_test"

    # Test Pause
    main_window.pause_current_task()
    state_mgr.update_lifecycle.assert_called_with("task_ui_test", TaskLifecycle.PAUSED)
    assert main_window.status_badge.text() == "PAUSED"

    # Test Resume
    main_window.resume_current_task()
    state_mgr.update_lifecycle.assert_called_with("task_ui_test", TaskLifecycle.EXECUTING)
    assert main_window.status_badge.text() == "EXECUTING"

    # Test Cancel
    main_window.cancel_current_task()
    state_mgr.cancel_task.assert_called_with("task_ui_test")
    assert main_window.status_badge.text() == "CANCELLED"
