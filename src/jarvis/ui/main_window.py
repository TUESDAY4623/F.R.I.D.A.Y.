from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from jarvis.logger import EventLogger, get_logger
from jarvis.orchestrator import AgentOrchestrator


class MainWindow(QMainWindow):
    """Phase 0 Jarvis UI.

    Provides:
    - text input
    - send button
    - agent response display
    - live Event Logger stream
    """

    log_signal = Signal(str)

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

        self.setWindowTitle("Jarvis - Desktop AI Agent")
        self.resize(900, 650)

        self._build_ui()

        # Thread-safe bridge from EventLogger callbacks
        # into the Qt UI thread.
        self.log_signal.connect(self._append_log)

        # Subscribe to live logger events.
        self.logger.add_subscriber(self._handle_event)

    def _build_ui(self) -> None:
        """Build the Phase 0 interface."""

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(10)

        # Title
        title = QLabel("JARVIS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold; padding: 8px;"
        )
        layout.addWidget(title)

        subtitle = QLabel("Desktop AI Agent")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # User input section
        input_label = QLabel("User Request")
        input_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(input_label)

        input_row = QHBoxLayout()

        self.input_box = QPlainTextEdit()
        self.input_box.setPlaceholderText("Type your command...")
        self.input_box.setMaximumHeight(90)

        self.send_button = QPushButton("Send")
        self.send_button.setMinimumWidth(100)

        input_row.addWidget(self.input_box)
        input_row.addWidget(self.send_button)

        layout.addLayout(input_row)

        # Agent response section
        response_label = QLabel("Agent Response")
        response_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(response_label)

        self.response_box = QPlainTextEdit()
        self.response_box.setReadOnly(True)
        self.response_box.setPlaceholderText(
            "Orchestrator result will appear here..."
        )

        layout.addWidget(self.response_box)

        # Live event log
        log_label = QLabel("Live Event Log")
        log_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(log_label)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

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

        try:
            result = self.orchestrator.execute_task(text)

            self.response_box.setPlainText(
                self._format_result(result)
            )

        except Exception as exc:
            self.response_box.setPlainText(
                f"Task failed:\n{exc}"
            )

        finally:
            self.send_button.setEnabled(True)
            self.input_box.clear()
            self.input_box.setFocus()

    def _handle_event(self, event: Any) -> None:
        """Receive EventLogger events and forward them to Qt."""

        self.log_signal.emit(event.to_log_line())

    def _append_log(self, line: str) -> None:
        """Append one event to the live log pane."""

        self.log_box.appendPlainText(line)

        scrollbar = self.log_box.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @staticmethod
    def _format_result(result: dict[str, Any]) -> str:
        """Format the orchestrator result for the Phase 0 UI."""

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