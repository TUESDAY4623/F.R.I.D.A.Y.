"""ApprovalDialog modal component for human-in-the-loop policy confirmations.

Per Section 4 & Section 7:
Presents action, target, consequences, reversibility, and policy risk reasons.
Returns ApprovalDecision (APPROVE, DENY, CANCEL).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jarvis.approval import ApprovalRequest
from jarvis.types import ApprovalDecision


class ApprovalDialog(QDialog):
    """Modal dialog prompting user for approval of medium/high risk actions."""

    def __init__(
        self,
        request: ApprovalRequest,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.request = request
        self.decision: ApprovalDecision = ApprovalDecision.DENY

        self.setWindowTitle("Jarvis — Human Approval Required")
        self.resize(520, 360)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title / Header
        header = QLabel("🔒 Security Policy Confirmation Required")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #856404;")
        layout.addWidget(header)

        sub_header = QLabel(
            "An action requires explicit confirmation before execution on your system."
        )
        sub_header.setWordWrap(True)
        sub_header.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(sub_header)

        # Details Card / Container
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            "background-color: #f8f9fa; border: 1px solid #e2e3e5; border-radius: 6px; padding: 12px;"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        # Action / Tool
        action_label = QLabel(f"<b>Action / Tool:</b> {self.request.action}")
        card_layout.addWidget(action_label)

        # Target Resource
        target_label = QLabel(f"<b>Target Resource:</b> {self.request.target}")
        target_label.setWordWrap(True)
        card_layout.addWidget(target_label)

        # Consequences
        consequences_label = QLabel(f"<b>Consequences:</b> {self.request.consequences}")
        consequences_label.setWordWrap(True)
        card_layout.addWidget(consequences_label)

        # Reversibility
        if self.request.reversible:
            rev_str = "<span style='color: #28a745; font-weight: bold;'>Reversible</span>"
        else:
            rev_str = "<span style='color: #dc3545; font-weight: bold;'>Irreversible (HIGH RISK)</span>"
        rev_label = QLabel(f"<b>Reversibility:</b> {rev_str}")
        card_layout.addWidget(rev_label)

        # Policy Reason
        reason_label = QLabel(f"<b>Policy Reason:</b> {self.request.reason}")
        reason_label.setWordWrap(True)
        card_layout.addWidget(reason_label)

        layout.addWidget(card)
        layout.addStretch()

        # Action Buttons Row
        button_row = QHBoxLayout()

        self.btn_approve = QPushButton("Approve")
        self.btn_approve.setStyleSheet(
            "background-color: #28a745; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;"
        )

        self.btn_deny = QPushButton("Deny")
        self.btn_deny.setStyleSheet(
            "background-color: #ffc107; color: black; font-weight: bold; padding: 8px 16px; border-radius: 4px;"
        )

        self.btn_cancel = QPushButton("Cancel Task")
        self.btn_cancel.setStyleSheet(
            "background-color: #dc3545; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;"
        )

        button_row.addWidget(self.btn_approve)
        button_row.addWidget(self.btn_deny)
        button_row.addWidget(self.btn_cancel)

        layout.addLayout(button_row)

        # Connections
        self.btn_approve.clicked.connect(self._on_approve)
        self.btn_deny.clicked.connect(self._on_deny)
        self.btn_cancel.clicked.connect(self._on_cancel)

    def _on_approve(self) -> None:
        self.decision = ApprovalDecision.APPROVE
        self.accept()

    def _on_deny(self) -> None:
        self.decision = ApprovalDecision.DENY
        self.reject()

    def _on_cancel(self) -> None:
        self.decision = ApprovalDecision.CANCEL
        self.reject()

    def get_decision(self) -> ApprovalDecision:
        return self.decision
