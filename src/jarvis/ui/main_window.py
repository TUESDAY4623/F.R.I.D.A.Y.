from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jarvis.logger import EventLogger, get_logger
from jarvis.orchestrator import AgentOrchestrator


class MainWindow(QMainWindow):
    """Phase 1 Jarvis Observability UI.

    Provides:
    - Text input & send controls
    - Live Task Lifecycle State Status Badge (CREATED -> UNDERSTANDING -> PLANNING -> EXECUTING -> COMPLETED/FAILED)
    - Structured Collapsible Tool Call Log Viewer (tool name, args, output/error)
    - Orchestrator response display
    - Live streaming Event Logger pane
    """

    log_signal = Signal(str)
    task_state_signal = Signal(str)
    tool_event_signal = Signal(dict)

    def __init__(
        self,
        orchestrator: AgentOrchestrator | None = None,
        logger: EventLogger | None = None,
    ) -> None:
        super().__init__()

        self.logger = logger or get_logger()
        self.orchestrator = orchestrator or AgentOrchestrator(
            logger=self.logger
        )

        self.setWindowTitle("Jarvis - Desktop AI Agent (Observability)")
        self.resize(950, 750)

        self._active_tool_items: dict[str, QTreeWidgetItem] = {}

        self._build_ui()

        # Thread-safe signal connections
        self.log_signal.connect(self._append_log)
        self.task_state_signal.connect(self._update_task_state)
        self.tool_event_signal.connect(self._handle_tool_event)

        # Subscribe to live logger events
        self.logger.add_subscriber(self._handle_event)

    def _build_ui(self) -> None:
        """Build the Phase 1 Observability Interface."""

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(10)

        # Top Header Bar (Title + Status Badge)
        header_layout = QHBoxLayout()

        title_container = QVBoxLayout()
        title = QLabel("JARVIS")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        subtitle = QLabel("Desktop AI Agent — Observability Control Shell")
        subtitle.setStyleSheet("color: #666; font-size: 12px;")
        title_container.addWidget(title)
        title_container.addWidget(subtitle)

        header_layout.addLayout(title_container)
        header_layout.addStretch()

        # Task State Status Line / Badge
        state_container = QHBoxLayout()
        state_title = QLabel("Task State:")
        state_title.setStyleSheet("font-weight: bold;")

        self.status_badge = QLabel("IDLE")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setMinimumWidth(130)
        self.status_badge.setStyleSheet(
            "background-color: #e0e0e0; color: #333; font-weight: bold; "
            "border-radius: 6px; padding: 6px 12px; font-size: 13px;"
        )

        state_container.addWidget(state_title)
        state_container.addWidget(self.status_badge)
        header_layout.addLayout(state_container)

        layout.addLayout(header_layout)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(divider)

        # User input section
        input_label = QLabel("User Request")
        input_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(input_label)

        input_row = QHBoxLayout()

        self.input_box = QPlainTextEdit()
        self.input_box.setPlaceholderText("Type your command...")
        self.input_box.setMaximumHeight(80)

        self.send_button = QPushButton("Send")
        self.send_button.setMinimumWidth(100)
        self.send_button.setStyleSheet("font-weight: bold; padding: 10px;")

        input_row.addWidget(self.input_box)
        input_row.addWidget(self.send_button)

        layout.addLayout(input_row)

        # Tool Call Log Viewer Section (Collapsible Tree View)
        tool_label = QLabel("Dispatched Tool Calls Log")
        tool_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(tool_label)

        self.tool_call_tree = QTreeWidget()
        self.tool_call_tree.setHeaderLabels(["Tool Name / Payload", "Status"])
        self.tool_call_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.tool_call_tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tool_call_tree.setMaximumHeight(160)
        layout.addWidget(self.tool_call_tree)

        # Agent response section
        response_label = QLabel("Agent Output Response")
        response_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(response_label)

        self.response_box = QPlainTextEdit()
        self.response_box.setReadOnly(True)
        self.response_box.setMaximumHeight(100)
        self.response_box.setPlaceholderText(
            "Orchestrator result will appear here..."
        )

        layout.addWidget(self.response_box)

        # Live event log section
        log_label = QLabel("Live Event Stream")
        log_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(log_label)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        layout.addWidget(self.log_box)

        # Connections
        self.send_button.clicked.connect(self.submit_request)

    def submit_request(self) -> None:
        """Submit the current user request to the orchestrator."""

        text = self.input_box.toPlainText().strip()

        if not text:
            return

        self.send_button.setEnabled(False)
        self.response_box.setPlainText("Running task...")
        self.tool_call_tree.clear()
        self._active_tool_items.clear()
        self._update_task_state("CREATED")

        try:
            result = self.orchestrator.execute_task(text)

            self.response_box.setPlainText(self._format_result(result))
            status = result.get("status", "COMPLETED")
            self._update_task_state(status)

        except Exception as exc:
            self.response_box.setPlainText(f"Task failed:\n{exc}")
            self._update_task_state("FAILED")

        finally:
            self.send_button.setEnabled(True)
            self.input_box.clear()
            self.input_box.setFocus()

    def _handle_event(self, event: Any) -> None:
        """Receive EventLogger events and forward them to Qt signals."""

        if hasattr(event, "to_log_line"):
            self.log_signal.emit(event.to_log_line())

        event_type = getattr(event, "event_type", None)
        event_type_val = (
            getattr(event_type, "value", str(event_type)) if event_type else ""
        )

        # Track Task Lifecycle & Loop State
        if event_type_val == "task.created":
            self.task_state_signal.emit("CREATED")
        elif event_type_val == "task.status_changed":
            payload = getattr(event, "payload", {}) or {}
            st = payload.get("status", "EXECUTING")
            self.task_state_signal.emit(str(st).upper())
        elif event_type_val == "task.completed":
            self.task_state_signal.emit("COMPLETED")
        elif event_type_val == "task.failed":
            self.task_state_signal.emit("FAILED")
        elif event_type_val == "task.cancelled":
            self.task_state_signal.emit("CANCELLED")

        # Map canonical steps to lifecycle phases if appropriate
        step_name = getattr(event, "step_name", None)
        if step_name:
            if "Observe current state" in step_name:
                self.task_state_signal.emit("UNDERSTANDING")
            elif "Decide next action" in step_name or "Policy check" in step_name:
                self.task_state_signal.emit("PLANNING")
            elif "Dispatch action" in step_name:
                self.task_state_signal.emit("EXECUTING")

        # Track Tool Dispatch Events
        if event_type_val in (
            "tool.requested",
            "tool.started",
            "tool.completed",
            "tool.failed",
            "orchestrator.step",
        ):
            payload = getattr(event, "payload", {}) or {}
            msg = getattr(event, "message", "")

            if "tool" in event_type_val or (step_name and "Dispatch" in step_name):
                tool_data = {
                    "type": event_type_val,
                    "step_name": step_name,
                    "message": msg,
                    "payload": payload,
                }
                self.tool_event_signal.emit(tool_data)

    def _update_task_state(self, state: str) -> None:
        """Update the task state status line / badge with color coding."""

        formatted_state = state.upper().strip()
        self.status_badge.setText(formatted_state)

        color_map = {
            "IDLE": ("#e0e0e0", "#333333"),
            "CREATED": ("#d1ecf1", "#0c5460"),
            "UNDERSTANDING": ("#cce5ff", "#004085"),
            "PLANNING": ("#fff3cd", "#856404"),
            "EXECUTING": ("#d4edda", "#155724"),
            "VERIFYING": ("#e2e3e5", "#383d41"),
            "COMPLETED": ("#28a745", "#ffffff"),
            "LOOP_COMPLETED": ("#28a745", "#ffffff"),
            "FAILED": ("#dc3545", "#ffffff"),
            "CANCELLED": ("#6c757d", "#ffffff"),
        }

        bg_color, text_color = color_map.get(
            formatted_state, ("#e0e0e0", "#333333")
        )

        self.status_badge.setStyleSheet(
            f"background-color: {bg_color}; color: {text_color}; font-weight: bold; "
            f"border-radius: 6px; padding: 6px 12px; font-size: 13px;"
        )

    def _handle_tool_event(self, tool_data: dict[str, Any]) -> None:
        """Add or update collapsible tool call log entries in the QTreeWidget."""

        event_type = tool_data.get("type", "")
        step_name = tool_data.get("step_name")
        payload = tool_data.get("payload", {})
        msg = tool_data.get("message", "")

        tool_name = (
            payload.get("tool_name")
            or payload.get("action")
            or (step_name if step_name else "Tool Action")
        )

        is_start = event_type in ("tool.started", "tool.requested") or (
            event_type == "orchestrator.step"
            and step_name
            and "Dispatch action" in step_name
            and tool_name not in self._active_tool_items
        )

        is_end = (
            event_type in ("tool.completed", "tool.failed")
            or "completed" in msg.lower()
            or "failed" in msg.lower()
        )

        if is_start:
            item = QTreeWidgetItem(self.tool_call_tree)
            item.setText(0, f"🔧 Tool Dispatch: {tool_name}")
            item.setText(1, "RUNNING")
            item.setForeground(1, Qt.GlobalColor.darkBlue)

            # Add arguments sub-item if available
            args = payload.get("arguments") or payload.get("args")
            if args:
                args_item = QTreeWidgetItem(item)
                args_item.setText(0, f"Arguments: {json.dumps(args)}")

            item.setExpanded(True)
            self._active_tool_items[tool_name] = item

        elif is_end:
            item = self._active_tool_items.pop(tool_name, None)
            if not item and self.tool_call_tree.topLevelItemCount() > 0:
                item = self.tool_call_tree.topLevelItem(
                    self.tool_call_tree.topLevelItemCount() - 1
                )

            if item:
                if event_type == "tool.failed" or "failed" in msg.lower():
                    item.setText(1, "FAILED")
                    item.setForeground(1, Qt.GlobalColor.red)
                    err = payload.get("error") or msg
                    err_item = QTreeWidgetItem(item)
                    err_item.setText(0, f"Error: {err}")
                else:
                    item.setText(1, "SUCCESS")
                    item.setForeground(1, Qt.GlobalColor.darkGreen)
                    result_data = payload.get("result") or payload.get("data")
                    if result_data:
                        res_item = QTreeWidgetItem(item)
                        res_item.setText(0, f"Result: {json.dumps(result_data)}")


    def _append_log(self, line: str) -> None:
        """Append one event to the live log pane."""

        self.log_box.appendPlainText(line)

        scrollbar = self.log_box.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @staticmethod
    def _format_result(result: dict[str, Any]) -> str:
        """Format the orchestrator result for the UI."""

        return (
            f"Task ID: {result.get('task_id')}\n"
            f"Success: {result.get('success')}\n"
            f"Status: {result.get('status')}\n"
            f"Steps executed: {result.get('steps_count')}\n"
        )


def run_app() -> int:
    """Start the Jarvis desktop application."""

    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_app())