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
from jarvis.contracts.models.group_c import (
    DECISION_ADAPTER,
    AgentState,
    AnyDecision,
    AnyDecisionUnion,
    AskUserDecision,
    AskUserParams,
    CompleteDecision,
    CompleteParams,
    DecisionType,
    ErrorRecord,
    ExecuteDecision,
    ExecuteParams,
    ExecutionStep,
    FailDecision,
    FailParams,
    Observation,
    ObserveDecision,
    ObserveParams,
    ReplanDecision,
    ReplanParams,
    RetryDecision,
    RetryParams,
    RuntimeConfig,
    TaskStatus,
    VerificationResult,
    WaitDecision,
    WaitParams,
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
    # Group C — enums
    "DecisionType",
    "TaskStatus",
    # Group C — nested contracts
    "ErrorRecord",
    "Observation",
    "VerificationResult",
    "ExecutionStep",
    # Group C — decision parameters
    "ExecuteParams",
    "ObserveParams",
    "ReplanParams",
    "RetryParams",
    "AskUserParams",
    "WaitParams",
    "CompleteParams",
    "FailParams",
    # Group C — decision variants
    "ExecuteDecision",
    "ObserveDecision",
    "ReplanDecision",
    "RetryDecision",
    "AskUserDecision",
    "WaitDecision",
    "CompleteDecision",
    "FailDecision",
    # Group C — union + adapter
    "AnyDecision",
    "AnyDecisionUnion",
    "DECISION_ADAPTER",
    # Group C — runtime
    "RuntimeConfig",
    "AgentState",
]
