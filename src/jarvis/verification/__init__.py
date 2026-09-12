"""Verification Engine module (Phase 0 stub).

Per Section 4 & Section 6:
- Verification Engine owns: Comparing observed state to expected outcome.
- Verification Engine does NOT own: Deciding recovery strategy (that's Error/Recovery Manager).
- Receives: Expected outcome, Observation.
- Returns: Success / Failure + reason.
- Called by: Orchestrator.
(To be fully implemented by Sujeet in Phase 2).
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel

from jarvis.observation import Observation
from jarvis.types import VerificationStatus


class VerificationResult(BaseModel):
    """Result of verification comparison."""

    status: VerificationStatus
    reason: str
    details: Dict[str, Any] = {}


class VerificationEngine:
    """Verification Engine stub."""

    def verify(
        self,
        expected_outcome: Dict[str, Any],
        observation: Observation,
    ) -> VerificationResult:
        """Compare observed state with expected outcome."""
        return VerificationResult(
            status=VerificationStatus.PASS,
            reason="Observation satisfies expected outcome (Phase 0 stub)",
            details={"observation": observation.state, "expected": expected_outcome},
        )


_default_verification_engine: Optional[VerificationEngine] = None


def get_verification_engine() -> VerificationEngine:
    global _default_verification_engine
    if _default_verification_engine is None:
        _default_verification_engine = VerificationEngine()
    return _default_verification_engine
