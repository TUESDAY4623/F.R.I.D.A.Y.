"""Observation Manager module (Phase 0 stub).

Per Section 4 & Section 6:
- Observation Manager owns: Selecting and normalizing the right observation source per surface.
- Observation Manager does NOT own: Deciding if the result satisfies the task (that's Verification).
- Receives: Request for "current state of X".
- Returns: Normalized Observation object.
- Called by: Orchestrator.
(To be fully implemented by Adarsh in Phase 2).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Observation(BaseModel):
    """Normalized observation object produced regardless of source."""

    source: str = "stub_source"
    state: Dict[str, Any] = Field(default_factory=dict)
    raw_data: Any = None
    deterministic_cache_hit: bool = False


class ObservationManager:
    """Observation Manager stub."""

    def observe(self, target: Optional[str] = None, skip_if_cached: bool = False) -> Observation:
        """Capture or retrieve normalized observation of the target."""
        return Observation(
            source="stub_observation_manager",
            state={"target": target or "desktop", "status": "nominal"},
            deterministic_cache_hit=skip_if_cached,
        )


_default_observation_manager: Optional[ObservationManager] = None


def get_observation_manager() -> ObservationManager:
    global _default_observation_manager
    if _default_observation_manager is None:
        _default_observation_manager = ObservationManager()
    return _default_observation_manager
