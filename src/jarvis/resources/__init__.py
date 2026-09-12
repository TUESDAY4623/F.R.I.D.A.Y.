"""Resource Manager module (Phase 0 stub).

Per Section 4 & Section 9:
- Resource Manager owns: Monitoring RAM/CPU/GPU/NPU, computing real memory budget
  (weights + KV cache + overhead), vetoing loads that would exceed budget.
- Resource Manager does NOT own: Model selection.
- Receives: Query for available headroom.
- Returns: Resource status.
- Called by: Model Manager, Orchestrator.
"""

from pydantic import BaseModel


class ResourceStatus(BaseModel):
    available_ram_gb: float = 10.0
    can_load_model: bool = True


class ResourceManager:
    """Resource Manager stub."""

    def check_headroom(self) -> ResourceStatus:
        return ResourceStatus()
