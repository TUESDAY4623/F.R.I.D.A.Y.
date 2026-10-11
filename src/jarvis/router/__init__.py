"""LLM Router module (Phase 0 stub).

Per Section 4 & Section 9:
- LLM Router owns: Choosing which model tier handles a request, using the routing function in §9.
- LLM Router does NOT own: Loading models, running inference (that's Model Manager / Inference Runtime).
- Receives: Task profile.
- Returns: Model selection.
- Called by: Planner, Orchestrator decide-step.
"""

from pydantic import BaseModel


class ModelSelection(BaseModel):
    tier: str = "local"
    model_name: str = "stub-model"


class LLMRouter:
    """LLM Router stub."""

    def route(self, task_profile: Any) -> ModelSelection:
        return ModelSelection(tier="local", model_name="stub-model")
