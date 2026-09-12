"""Policy Engine module (Phase 0 stub).

Per Section 4 & Section 7:
- Policy Engine owns: ALLOW / CONFIRM / DENY decision by risk tier.
- Policy Engine does NOT own: Talking to the user (that's Approval Manager).
- Receives: Proposed action + tool risk metadata.
- Returns: PolicyDecision (ALLOW, CONFIRM, DENY).
- Called by: Tool Manager / Orchestrator.
Per Phase 0 instructions: Empty pass-through (always ALLOW) until Phase 1.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from jarvis.tools.contract import ToolContract
from jarvis.types import PolicyDecision


class PolicyEngine:
    """Policy Engine stub: Pass-through ALLOW for Phase 0."""

    def check(self, action_name: str, arguments: Dict[str, Any], contract: Optional[ToolContract] = None) -> PolicyDecision:
        """Evaluate policy for proposed action."""
        # Phase 0 pass-through stub
        return PolicyDecision.ALLOW


_default_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    global _default_policy_engine
    if _default_policy_engine is None:
        _default_policy_engine = PolicyEngine()
    return _default_policy_engine
