"""
Jarvis Core Contracts.

Source of truth for all data contracts in the Jarvis agentic desktop AI system.
Pydantic models define the contracts; JSON schemas are generated from them.
"""

from jarvis.contracts.models.group_a import (
    EntityType,
    ExtractedEntity,
    Intent,
    LayaCategory,
    LayaClassification,
    Request,
    RequestCharacteristic,
)
from jarvis.contracts.models.group_b import (
    Complexity,
    EdgeType,
    NodeStatus,
    TaskGraph,
    TaskGraphEdge,
    TaskGraphNode,
    TaskProfile,
    TaskType,
)

__all__ = [
    # Group A
    "EntityType",
    "ExtractedEntity",
    "Intent",
    "LayaCategory",
    "LayaClassification",
    "Request",
    "RequestCharacteristic",
    # Group B
    "Complexity",
    "EdgeType",
    "NodeStatus",
    "TaskGraph",
    "TaskGraphEdge",
    "TaskGraphNode",
    "TaskProfile",
    "TaskType",
]
