"""
Group B contracts: Task Understanding layer.

Models:
- TaskProfile: Task characteristics and requirements from the Task Profiler.
- TaskGraph: Execution strategy from the Planner.
- TaskGraphNode: A single step in the task graph.
- TaskGraphEdge: Dependency relationship between nodes.
- Enums: TaskType, Complexity, NodeStatus, EdgeType.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from jarvis.contracts.models.base import JarvisBaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskType(StrEnum):
    """High-level classification of task structure."""

    SINGLE_STEP = "single-step"
    MULTI_STEP = "multi-step"
    EXPLORATORY = "exploratory"


class Complexity(StrEnum):
    """Task Profiler's assessment of task complexity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NodeStatus(StrEnum):
    """Lifecycle status of a TaskGraph node."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class EdgeType(StrEnum):
    """Type of dependency relationship between graph nodes."""

    SEQUENCE = "sequence"
    CONDITION = "condition"
    ALTERNATIVE = "alternative"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TaskProfile(JarvisBaseModel):
    """Output of the Task Profiler.

    Task complexity analysis lives here, not in LayaClassification.
    This model describes what the task needs and how complex it is.
    It does not contain execution steps, tool calls, graph nodes,
    graph edges, agent decisions, or runtime state.
    """

    intent_id: str = Field(
        ...,
        min_length=1,
        description="Links back to the originating Intent.",
    )
    task_type: TaskType = Field(
        ...,
        description="High-level task structure (e.g., single-step, multi-step, exploratory).",
    )
    requirements: list[str] = Field(
        default_factory=list,
        description="What the task needs (tools, data, etc.).",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Task-specific constraints.",
    )
    complexity: Complexity = Field(
        ...,
        description="Task Profiler's assessment of task complexity.",
    )
    estimated_steps: int = Field(
        ...,
        gt=0,
        description="Informational hint only. The Planner determines the actual step count.",
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Conditions that must be met before execution.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional profiling details.",
    )


class TaskGraphNode(JarvisBaseModel):
    """A single step in the task execution graph.

    Represents a task objective using only documented fields.
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique node identifier.",
    )
    type: str = Field(
        ...,
        min_length=1,
        description="Action type (e.g., tool_call, observe, ask_user).",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of this step.",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the action.",
    )
    expected_outcome: str = Field(
        ...,
        min_length=1,
        description="What success looks like.",
    )
    retry_limit: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts.",
    )
    status: NodeStatus = Field(
        default=NodeStatus.PENDING,
        description="Current lifecycle status of this node.",
    )
    result: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution result (populated after execution).",
    )


class TaskGraphEdge(JarvisBaseModel):
    """A dependency relationship between two graph nodes.

    The `from_` field references the source node ID. The `to` field
    references the target node ID. Edge type describes the relationship.

    The Python attribute is `from_` because `from` is a reserved keyword.
    The documented external contract name is `from`, which is enforced
    via the alias. `populate_by_name=True` keeps `from_` accepted on
    input for Python-side construction; `serialize_by_alias=True` makes
    `model_dump()` / `model_dump_json()` emit the documented `from` name
    by default so the output conforms to the generated JSON schema.
    """

    from_: str = Field(
        ...,
        alias="from",
        min_length=1,
        description="Source node ID.",
    )
    to: str = Field(
        ...,
        min_length=1,
        description="Target node ID.",
    )
    type: EdgeType = Field(
        ...,
        description="Type of dependency: sequence, condition, or alternative.",
    )

    model_config = {
        **JarvisBaseModel.model_config,
        "populate_by_name": True,
        "serialize_by_alias": True,
    }


class TaskGraph(JarvisBaseModel):
    """Execution strategy constructed by the Planner.

    Represents the Planner's proposed execution structure.
    It does not contain live AgentState or decide how execution
    proceeds at runtime.
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this graph.",
    )
    nodes: list[TaskGraphNode] = Field(
        default_factory=list,
        description="Ordered list of steps in the task.",
    )
    edges: list[TaskGraphEdge] = Field(
        default_factory=list,
        description="Dependency relationships between nodes.",
    )
    entry_node_id: str = Field(
        ...,
        min_length=1,
        description="ID of the first node to execute.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Graph-level metadata.",
    )

    @model_validator(mode="after")
    def check_edge_references_valid(self) -> "TaskGraph":
        """Edge from_/to must reference existing node IDs in the graph."""
        node_ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.from_ not in node_ids:
                raise ValueError(
                    f"Edge references source node '{edge.from_}' which does not exist in the graph."
                )
            if edge.to not in node_ids:
                raise ValueError(
                    f"Edge references target node '{edge.to}' which does not exist in the graph."
                )
        return self

    @model_validator(mode="after")
    def check_entry_node_exists(self) -> "TaskGraph":
        """entry_node_id must reference a node in the graph."""
        node_ids = {node.id for node in self.nodes}
        if self.entry_node_id not in node_ids:
            raise ValueError(
                f"entry_node_id '{self.entry_node_id}' does not match any node in the graph."
            )
        return self

    @model_validator(mode="after")
    def check_unique_node_ids(self) -> "TaskGraph":
        """All node IDs must be unique."""
        node_ids = [node.id for node in self.nodes]
        seen: set[str] = set()
        for node_id in node_ids:
            if node_id in seen:
                raise ValueError(f"Duplicate node ID: '{node_id}'. Node IDs must be unique.")
            seen.add(node_id)
        return self
