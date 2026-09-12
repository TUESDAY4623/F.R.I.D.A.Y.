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

from typing import Any, Dict, Optional

from jarvis.types import ApprovalDecision


class ApprovalRequest:
    def __init__(
        self,
        action: str,
        target: str,
        consequences: str,
        reversible: bool,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.action = action
        self.target = target
        self.consequences = consequences
        self.reversible = reversible
        self.reason = reason
        self.metadata = metadata or {}


class ApprovalManager:
    """Approval Manager stub."""

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Present approval request to user and capture decision."""
        # Phase 0 stub auto-approves
        return ApprovalDecision.APPROVE


_default_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    global _default_approval_manager
    if _default_approval_manager is None:
        _default_approval_manager = ApprovalManager()
    return _default_approval_manager
