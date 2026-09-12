"""Task Profiler module (Phase 0 stub).

Per Section 4 & Section 9:
- Task Profiler owns: Structured requirements profile (complexity, risk, privacy, latency,
  vision, internet, context size, reasoning, reliability).
- Task Profiler does NOT own: Choosing a model.
- Receives: Intent.
- Returns: Task profile object.
- Called by: Intent Manager, before Planner/Router.
"""

from pydantic import BaseModel


class TaskProfile(BaseModel):
    complexity: str = "low"
    risk: str = "low"
    privacy: str = "normal"
    latency: str = "normal"
    vision_required: bool = False
    internet_required: bool = False
    reasoning_depth: str = "low"


class TaskProfiler:
    """Task Profiler stub."""

    def profile_task(self, intent: str) -> TaskProfile:
        return TaskProfile()
