"""Policy Engine for risk-based tool authorization."""

from __future__ import annotations

from typing import Any, Dict, Optional

from jarvis.tools.contract import ToolContract
from jarvis.types import PolicyDecision, RiskLevel


class PolicyEngine:
    """Evaluate proposed tool actions according to their risk level."""

    def check(
        self,
        action_name: str,
        arguments: Dict[str, Any],
        contract: Optional[ToolContract] = None,
    ) -> PolicyDecision:
        """Return ALLOW, CONFIRM, or DENY based on the tool risk level."""

        if contract is None:
            return PolicyDecision.DENY

        if contract.risk_level == RiskLevel.LOW:
            return PolicyDecision.ALLOW

        if contract.risk_level == RiskLevel.MEDIUM:
            return PolicyDecision.CONFIRM

        if contract.risk_level == RiskLevel.HIGH:
            return PolicyDecision.DENY

        return PolicyDecision.DENY


_default_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Return the shared default Policy Engine instance."""

    global _default_policy_engine

    if _default_policy_engine is None:
        _default_policy_engine = PolicyEngine()

    return _default_policy_engine
