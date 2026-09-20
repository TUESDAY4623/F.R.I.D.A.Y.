"""Approval Manager module (Phase 0 stub).

Per Section 4 & Section 7:
- Approval Manager owns: Human-in-the-loop interaction: presenting what/target/consequences/reversibility/why.
- Approval Manager does NOT own: Deciding risk tier (that's Policy Engine).
- Receives: Approval request from Policy Engine.
- Returns: ApprovalDecision (Approve / Deny / Cancel).
- Called by: Policy Engine / Orchestrator.
(To be fully implemented by Tanmay in Phase 2).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from jarvis.types import ApprovalDecision, ApprovalStatus


class ApprovalRequest:
    def __init__(
        self,
        action: str,
        target: str,
        consequences: str,
        reversible: bool,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
        status: ApprovalStatus = ApprovalStatus.PENDING,
    ) -> None:
        self.action = action
        self.target = target
        self.consequences = consequences
        self.reversible = reversible
        self.reason = reason
        self.metadata = metadata or {}
        self.status = status
        self.decision: Optional[ApprovalDecision] = None


class ApprovalManager:
    """Approval Manager handling human-in-the-loop decisions."""

    def __init__(self) -> None:
        self._default_decision: ApprovalDecision = ApprovalDecision.APPROVE
        self._handler: Optional[Callable[[ApprovalRequest], ApprovalDecision]] = None
        self._history: List[ApprovalRequest] = []

    def set_decision_handler(
        self, handler: Optional[Callable[[ApprovalRequest], ApprovalDecision]]
    ) -> None:
        """Register a custom decision handler callback (e.g. UI dialog or test mock)."""
        self._handler = handler

    def set_default_decision(self, decision: ApprovalDecision) -> None:
        """Set default decision when no custom handler is configured."""
        self._default_decision = decision

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Present approval request to user and capture decision."""
        request.status = ApprovalStatus.PENDING

        if self._handler is not None:
            decision = self._handler(request)
        else:
            decision = self._default_decision

        request.decision = decision
        if decision == ApprovalDecision.APPROVE:
            request.status = ApprovalStatus.APPROVED
        elif decision == ApprovalDecision.DENY:
            request.status = ApprovalStatus.DENIED
        elif decision == ApprovalDecision.CANCEL:
            request.status = ApprovalStatus.CANCELLED

        self._history.append(request)
        return decision

    @property
    def history(self) -> List[ApprovalRequest]:
        return list(self._history)

    def reset(self) -> None:
        self._default_decision = ApprovalDecision.APPROVE
        self._handler = None
        self._history.clear()


_default_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    global _default_approval_manager
    if _default_approval_manager is None:
        _default_approval_manager = ApprovalManager()
    return _default_approval_manager
