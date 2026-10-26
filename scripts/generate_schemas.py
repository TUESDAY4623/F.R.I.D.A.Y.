"""Generate JSON schemas from Jarvis Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

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
    DecisionType,
    TaskStatus,
    ErrorRecord,
    Observation,
    VerificationResult,
    ExecutionStep,
    ExecuteParams,
    ObserveParams,
    ReplanParams,
    RetryParams,
    AskUserParams,
    WaitParams,
    CompleteParams,
    FailParams,
    ExecuteDecision,
    ObserveDecision,
    ReplanDecision,
    RetryDecision,
    AskUserDecision,
    WaitDecision,
    CompleteDecision,
    FailDecision,
    DECISION_ADAPTER,
    RuntimeConfig,
    AgentState,
)
from jarvis.contracts.models.group_d import (
    ValidationError_,
    ValidationResult,
    ProposedAction,
    PolicyResult,
    ToolResult,
)
from jarvis.contracts.models.group_e import (
    UserResponse,
    WaitCondition,
    WaitConditionType,
)


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def write_schema(model, filename: str) -> Path:
    """Generate and write JSON schema for a Pydantic model."""
    schema = model.model_json_schema()
    return _write_schema_dict(schema, filename)


def write_adapter_schema(adapter, filename: str) -> Path:
    """Generate and write JSON schema from a Pydantic TypeAdapter.

    Used for annotated unions, where the discriminated-union shape (`oneOf`
    plus `discriminator`) is derived from the models rather than hand-written.
    """
    schema = adapter.json_schema()
    return _write_schema_dict(schema, filename)


def _write_schema_dict(schema: dict, filename: str) -> Path:
    out_path = SCHEMA_DIR / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    return out_path


def generate_all() -> None:
    """Generate JSON schemas for all contract models."""
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

    generated = []

    # Group A schemas
    generated.append(("request", write_schema(Request, "request.json")))
    generated.append(("extracted-entity", write_schema(ExtractedEntity, "extracted-entity.json")))
    generated.append(("laya-classification", write_schema(LayaClassification, "laya-classification.json")))
    generated.append(("intent", write_schema(Intent, "intent.json")))

    # Group B schemas
    generated.append(("task-profile", write_schema(TaskProfile, "task-profile.json")))
    generated.append(("task-graph-node", write_schema(TaskGraphNode, "task-graph-node.json")))
    generated.append(("task-graph-edge", write_schema(TaskGraphEdge, "task-graph-edge.json")))
    generated.append(("task-graph", write_schema(TaskGraph, "task-graph.json")))

    # Group C — nested contracts
    generated.append(("error-record", write_schema(ErrorRecord, "error-record.json")))
    generated.append(("observation", write_schema(Observation, "observation.json")))
    generated.append(("verification-result", write_schema(VerificationResult, "verification-result.json")))
    generated.append(("execution-step", write_schema(ExecutionStep, "execution-step.json")))

    # Group C — decision parameter models
    generated.append(("execute-params", write_schema(ExecuteParams, "execute-params.json")))
    generated.append(("observe-params", write_schema(ObserveParams, "observe-params.json")))
    generated.append(("replan-params", write_schema(ReplanParams, "replan-params.json")))
    generated.append(("retry-params", write_schema(RetryParams, "retry-params.json")))
    generated.append(("ask-user-params", write_schema(AskUserParams, "ask-user-params.json")))
    generated.append(("wait-params", write_schema(WaitParams, "wait-params.json")))
    generated.append(("complete-params", write_schema(CompleteParams, "complete-params.json")))
    generated.append(("fail-params", write_schema(FailParams, "fail-params.json")))

    # Group C — decision variants (one schema per type)
    for decision_cls, name in [
        (ExecuteDecision, "execute-decision"),
        (ObserveDecision, "observe-decision"),
        (ReplanDecision, "replan-decision"),
        (RetryDecision, "retry-decision"),
        (AskUserDecision, "ask-user-decision"),
        (WaitDecision, "wait-decision"),
        (CompleteDecision, "complete-decision"),
        (FailDecision, "fail-decision"),
    ]:
        generated.append((name, write_schema(decision_cls, f"{name}.json")))

    # Group C — top-level Decision union (ADR 04 names this schema file explicitly).
    # Generated from the annotated union so `oneOf` and the `type` discriminator
    # come from the Pydantic models — never hand-maintained.
    generated.append(("decision", write_adapter_schema(DECISION_ADAPTER, "decision.json")))

    # Group C — runtime
    generated.append(("runtime-config", write_schema(RuntimeConfig, "runtime-config.json")))
    generated.append(("agent-state", write_schema(AgentState, "agent-state.json")))

    # Group D — validation
    generated.append(("validation-error", write_schema(ValidationError_, "validation-error.json")))
    generated.append(("validation-result", write_schema(ValidationResult, "validation-result.json")))

    # Group D — execution boundary
    generated.append(("proposed-action", write_schema(ProposedAction, "proposed-action.json")))
    generated.append(("policy-result", write_schema(PolicyResult, "policy-result.json")))
    generated.append(("tool-result", write_schema(ToolResult, "tool-result.json")))

    # Group E — user interaction
    generated.append(("user-response", write_schema(UserResponse, "user-response.json")))
    generated.append(("wait-condition", write_schema(WaitCondition, "wait-condition.json")))

    # Enums as simple string schemas
    for name, enum_cls in [
        ("entity-type", EntityType),
        ("request-characteristic", RequestCharacteristic),
        ("laya-category", LayaCategory),
        ("task-type", TaskType),
        ("complexity", Complexity),
        ("node-status", NodeStatus),
        ("edge-type", EdgeType),
        ("decision-type", DecisionType),
        ("task-status", TaskStatus),
        ("wait-condition-type", WaitConditionType),
    ]:
        enum_schema = {
            "type": "string",
            "enum": [v.value for v in enum_cls],
            "description": enum_cls.__doc__ or f"Enum: {enum_cls.__name__}",
        }
        out_path = SCHEMA_DIR / f"{name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(enum_schema, f, indent=2)
        generated.append((name, out_path))

    print(f"Generated {len(generated)} schemas in {SCHEMA_DIR}")
    for name, path in generated:
        print(f"  {name}: {path}")


if __name__ == "__main__":
    generate_all()
