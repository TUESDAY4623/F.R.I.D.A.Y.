"""Tests for Group C contracts: Agent Runtime layer."""

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from pydantic import TypeAdapter, ValidationError

from jarvis.contracts.models.group_a import (
    Intent,
    LayaCategory,
    LayaClassification,
    Request,
)
from jarvis.contracts.models.group_b import (
    TaskGraph,
    TaskGraphNode,
    TaskProfile,
)
from jarvis.contracts.models.group_c import (
    DECISION_ADAPTER,
    AgentState,
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


SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"

ADAPTER: TypeAdapter = DECISION_ADAPTER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_schema(name: str) -> dict:
    """Load a generated JSON schema file."""
    path = SCHEMA_DIR / name
    assert path.exists(), f"Schema file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_error_record(**overrides: Any) -> ErrorRecord:
    data = {"code": "ERR001", "message": "test error", "recoverable": True}
    data.update(overrides)
    return ErrorRecord(**data)


def make_request(request_id: str = "req-1") -> Request:
    return Request(id=request_id, raw_input="do it", normalized_input="do it")


def make_laya(request_id: str = "req-1") -> LayaClassification:
    return LayaClassification(
        request_id=request_id,
        category=LayaCategory.ACTIONABLE,
        confidence=0.9,
        ambiguous=False,
    )


def make_intent(request_id: str = "req-1") -> Intent:
    return Intent(
        request_id=request_id,
        laya_category=LayaCategory.ACTIONABLE,
        normalized_form="do it",
        confidence=0.9,
        ambiguous=False,
    )


def make_profile(intent_id: str = "req-1") -> TaskProfile:
    return TaskProfile(
        intent_id=intent_id,
        task_type="single-step",
        complexity="low",
        estimated_steps=1,
    )


def make_graph() -> TaskGraph:
    node = TaskGraphNode(id="n1", type="tool_call", description="step", expected_outcome="done")
    return TaskGraph(id="g1", nodes=[node], edges=[], entry_node_id="n1")


def make_agent_state(**overrides: Any) -> AgentState:
    data: dict[str, Any] = {
        "request": make_request(),
        "intent": make_intent(),
        "laya_classification": make_laya(),
        "task_profile": make_profile(),
        "task_graph": make_graph(),
    }
    data.update(overrides)
    return AgentState(**data)


def make_decision_payload(**overrides: Any) -> dict[str, Any]:
    """A minimal valid EXECUTE decision payload."""
    data: dict[str, Any] = {
        "id": "dec-1",
        "type": "EXECUTE",
        "reasoning": "proceed with step",
        "confidence": 0.9,
        "parameters": {"target_node_id": "n1"},
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_decision_type_values(self) -> None:
        assert [t.value for t in DecisionType] == [
            "EXECUTE", "OBSERVE", "REPLAN", "RETRY",
            "ASK_USER", "WAIT", "COMPLETE", "FAIL",
        ]

    def test_task_status_values(self) -> None:
        assert [s.value for s in TaskStatus] == [
            "PENDING", "OBSERVING", "DECIDING", "EXECUTING", "VERIFYING",
            "REPLANNING", "AWAITING", "COMPLETED", "FAILED", "CANCELLED",
        ]


# ---------------------------------------------------------------------------
# RuntimeConfig
# ---------------------------------------------------------------------------


class TestRuntimeConfig:
    def test_defaults(self) -> None:
        cfg = RuntimeConfig()
        assert cfg.max_retries == 3
        assert cfg.max_replans == 3
        assert cfg.global_timeout_ms is None

    def test_explicit_values(self) -> None:
        cfg = RuntimeConfig(max_retries=5, max_replans=2, global_timeout_ms=60_000)
        assert cfg.max_retries == 5
        assert cfg.max_replans == 2
        assert cfg.global_timeout_ms == 60_000

    def test_negative_max_retries_fails(self) -> None:
        with pytest.raises(ValidationError):
            RuntimeConfig(max_retries=-1)

    def test_zero_timeout_fails(self) -> None:
        with pytest.raises(ValidationError):
            RuntimeConfig(global_timeout_ms=0)

    def test_extra_field_fails(self) -> None:
        with pytest.raises(ValidationError):
            RuntimeConfig(max_nodes=10)


# ---------------------------------------------------------------------------
# ErrorRecord / Observation / VerificationResult
# ---------------------------------------------------------------------------


class TestErrorRecord:
    def test_valid_minimal(self) -> None:
        err = make_error_record()
        assert err.code == "ERR001"
        assert err.recoverable is True
        assert err.context == {}
        assert err.timestamp is not None

    def test_empty_code_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_error_record(code="")

    def test_extra_field_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_error_record(traceback="...")

    def test_roundtrip(self) -> None:
        err = make_error_record()
        assert ErrorRecord.model_validate(err.model_dump(mode="json")) == err


class TestObservation:
    def test_valid_success(self) -> None:
        obs = Observation(source="tool", data={"out": 1}, success=True)
        assert obs.success is True
        assert obs.error is None

    def test_failure_requires_error(self) -> None:
        with pytest.raises(ValidationError):
            Observation(source="tool", data={}, success=False)

    def test_failure_with_error_ok(self) -> None:
        obs = Observation(source="tool", data={}, success=False, error=make_error_record())
        assert obs.error is not None

    def test_empty_source_fails(self) -> None:
        with pytest.raises(ValidationError):
            Observation(source="", success=True)

    def test_roundtrip(self) -> None:
        obs = Observation(source="tool", success=True)
        assert Observation.model_validate(obs.model_dump(mode="json")) == obs


class TestVerificationResult:
    def test_valid_passed(self) -> None:
        v = VerificationResult(passed=True)
        assert v.passed is True
        assert v.severity == "none"

    def test_severities(self) -> None:
        for sev in ("none", "warning", "error"):
            assert VerificationResult(passed=False, severity=sev).severity == sev

    def test_invalid_severity_fails(self) -> None:
        with pytest.raises(ValidationError):
            VerificationResult(passed=True, severity="critical")

    def test_roundtrip(self) -> None:
        v = VerificationResult(passed=False, discrepancy="mismatch")
        assert VerificationResult.model_validate(v.model_dump(mode="json")) == v


# ---------------------------------------------------------------------------
# ExecutionStep
# ---------------------------------------------------------------------------


class TestExecutionStep:
    def _step(self, **overrides: Any) -> ExecutionStep:
        data: dict[str, Any] = {
            "step_number": 1,
            "node_id": "n1",
            "decision": make_decision_payload(),
            "action": "ran tool",
            "observation": {"source": "tool", "success": True, "data": {}},
            "verification": {"passed": True},
            "duration_ms": 42,
        }
        data.update(overrides)
        return ExecutionStep(**data)

    def test_valid(self) -> None:
        step = self._step()
        assert step.step_number == 1
        assert step.node_id == "n1"
        assert isinstance(step.decision, ExecuteDecision)
        assert step.duration_ms == 42

    def test_zero_step_number_fails(self) -> None:
        with pytest.raises(ValidationError):
            self._step(step_number=0)

    def test_negative_duration_fails(self) -> None:
        with pytest.raises(ValidationError):
            self._step(duration_ms=-1)

    def test_roundtrip(self) -> None:
        step = self._step()
        assert ExecutionStep.model_validate(step.model_dump(mode="json")) == step


# ---------------------------------------------------------------------------
# Decision parameter models (direct construction)
# ---------------------------------------------------------------------------


class TestDecisionParams:
    def test_execute_params(self) -> None:
        p = ExecuteParams(target_node_id="n1", tool_params={"a": 1})
        assert p.target_node_id == "n1"
        assert p.tool_params == {"a": 1}

    def test_execute_params_missing_target_fails(self) -> None:
        with pytest.raises(ValidationError):
            ExecuteParams()

    def test_observe_params(self) -> None:
        p = ObserveParams(observation_target="screen", observation_params={"dpi": 1})
        assert p.observation_target == "screen"

    def test_replan_params(self) -> None:
        p = ReplanParams(replan_reason="changed")
        assert p.preserve_completed is True

    def test_replan_params_missing_reason_fails(self) -> None:
        with pytest.raises(ValidationError):
            ReplanParams()

    def test_retry_params(self) -> None:
        p = RetryParams(target_node_id="n1", retry_count=2)
        assert p.retry_count == 2
        assert p.adjusted_params == {}

    def test_retry_params_zero_count_fails(self) -> None:
        with pytest.raises(ValidationError):
            RetryParams(target_node_id="n1", retry_count=0)

    def test_ask_user_params(self) -> None:
        p = AskUserParams(question="ok?", options=["yes", "no"])
        assert p.required is True
        assert p.options == ["yes", "no"]

    def test_ask_user_params_missing_question_fails(self) -> None:
        with pytest.raises(ValidationError):
            AskUserParams()

    def test_wait_params(self) -> None:
        p = WaitParams(condition="file appears", timeout_ms=1000)
        assert p.timeout_ms == 1000

    def test_wait_params_zero_timeout_fails(self) -> None:
        with pytest.raises(ValidationError):
            WaitParams(condition="x", timeout_ms=0)

    def test_complete_params(self) -> None:
        p = CompleteParams(summary="done", result={"ok": True})
        assert p.summary == "done"

    def test_fail_params(self) -> None:
        p = FailParams(reason="nope")
        assert p.error is None

    def test_fail_params_missing_reason_fails(self) -> None:
        with pytest.raises(ValidationError):
            FailParams()

    def test_all_params_forbid_extra(self) -> None:
        with pytest.raises(ValidationError):
            ExecuteParams(target_node_id="n1", junk=1)


# ---------------------------------------------------------------------------
# Discriminated union — all eight types valid
# ---------------------------------------------------------------------------


class TestDecisionUnionValid:
    """Every decision type has at least one valid case."""

    def test_execute(self) -> None:
        d = ADAPTER.validate_python(make_decision_payload())
        assert isinstance(d, ExecuteDecision)
        assert isinstance(d.parameters, ExecuteParams)
        assert d.parameters.target_node_id == "n1"

    def test_observe(self) -> None:
        d = ADAPTER.validate_python(
            make_decision_payload(type="OBSERVE", parameters={"observation_target": "screen"})
        )
        assert isinstance(d, ObserveDecision)
        assert d.parameters.observation_target == "screen"

    def test_observe_empty_parameters(self) -> None:
        d = ADAPTER.validate_python(
            make_decision_payload(type="OBSERVE", parameters={})
        )
        assert isinstance(d, ObserveDecision)

    def test_replan(self) -> None:
        d = ADAPTER.validate_python(
            make_decision_payload(type="REPLAN", parameters={"replan_reason": "changed"})
        )
        assert isinstance(d, ReplanDecision)
        assert d.parameters.preserve_completed is True

    def test_retry(self) -> None:
        d = ADAPTER.validate_python(
            make_decision_payload(
                type="RETRY",
                parameters={"target_node_id": "n1", "retry_count": 1},
            )
        )
        assert isinstance(d, RetryDecision)
        assert d.parameters.retry_count == 1

    def test_ask_user(self) -> None:
        d = ADAPTER.validate_python(
            make_decision_payload(type="ASK_USER", parameters={"question": "proceed?"})
        )
        assert isinstance(d, AskUserDecision)

    def test_wait(self) -> None:
        d = ADAPTER.validate_python(
            make_decision_payload(type="WAIT", parameters={"condition": "file", "timeout_ms": 500})
        )
        assert isinstance(d, WaitDecision)

    def test_complete(self) -> None:
        d = ADAPTER.validate_python(
            make_decision_payload(type="COMPLETE", parameters={"summary": "done"})
        )
        assert isinstance(d, CompleteDecision)

    def test_fail(self) -> None:
        d = ADAPTER.validate_python(
            make_decision_payload(type="FAIL", parameters={"reason": "unrecoverable"})
        )
        assert isinstance(d, FailDecision)


# ---------------------------------------------------------------------------
# Discriminated union — every type has at least one invalid case
# ---------------------------------------------------------------------------


class TestDecisionUnionInvalid:
    """Every decision type has at least one rejected case."""

    def test_execute_missing_target_node_id(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(
                make_decision_payload(type="EXECUTE", parameters={})
            )

    def test_observe_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(
                make_decision_payload(
                    type="OBSERVE", parameters={"observation_target": "x", "junk": 1}
                )
            )

    def test_replan_missing_reason(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(make_decision_payload(type="REPLAN", parameters={}))

    def test_retry_missing_retry_count(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(
                make_decision_payload(type="RETRY", parameters={"target_node_id": "n1"})
            )

    def test_ask_user_missing_question(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(make_decision_payload(type="ASK_USER", parameters={}))

    def test_wait_missing_timeout(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(
                make_decision_payload(type="WAIT", parameters={"condition": "x"})
            )

    def test_complete_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(
                make_decision_payload(type="COMPLETE", parameters={"score": 1})
            )

    def test_fail_missing_reason(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(make_decision_payload(type="FAIL", parameters={}))


# ---------------------------------------------------------------------------
# Union selection, unknown types, extra fields, type errors
# ---------------------------------------------------------------------------


class TestUnionSelectionAndRejection:
    def test_unknown_decision_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(make_decision_payload(type="TELEPORT"))

    def test_missing_type_rejected(self) -> None:
        payload = make_decision_payload()
        del payload["type"]
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(payload)

    def test_extra_top_level_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(make_decision_payload(junk=1))

    def test_extra_parameter_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(
                make_decision_payload(parameters={"target_node_id": "n1", "junk": 1})
            )

    def test_invalid_parameter_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(
                make_decision_payload(parameters={"target_node_id": 123})
            )

    def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(make_decision_payload(confidence=1.5))

    def test_empty_reasoning_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(make_decision_payload(reasoning="   "))

    def test_missing_id_rejected(self) -> None:
        payload = make_decision_payload()
        del payload["id"]
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(payload)

    def test_parameters_not_a_dict_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(make_decision_payload(parameters="nope"))

    def test_selection_is_type_driven(self) -> None:
        """Same `type` field selects the same variant regardless of field order."""
        d = ADAPTER.validate_python(
            {
                "parameters": {"target_node_id": "n1"},
                "confidence": 0.5,
                "reasoning": "r",
                "id": "d",
                "type": "EXECUTE",
            }
        )
        assert isinstance(d, ExecuteDecision)


# ---------------------------------------------------------------------------
# Retry-count authority (ADR 04 / ADR 06 / ADR 11)
# ---------------------------------------------------------------------------


class TestRetryCountAuthority:
    def test_decision_retry_count_is_optional_at_top_level(self) -> None:
        d = ADAPTER.validate_python(make_decision_payload())
        assert d.retry_count is None
        assert d.target_node_id is None

    def test_retry_params_retry_count_is_informational(self) -> None:
        """Decision retry_count may disagree with AgentState — no cross-field rule."""
        d = ADAPTER.validate_python(
            make_decision_payload(
                type="RETRY",
                retry_count=99,
                parameters={"target_node_id": "n1", "retry_count": 1},
            )
        )
        assert d.retry_count == 99
        assert d.parameters.retry_count == 1

    def test_top_level_retry_count_minimum_is_one(self) -> None:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(make_decision_payload(retry_count=0))


# ---------------------------------------------------------------------------
# AgentState
# ---------------------------------------------------------------------------


class TestAgentState:
    def test_valid_defaults(self) -> None:
        state = make_agent_state()
        assert state.status == TaskStatus.PENDING
        assert state.retry_count == 0
        assert state.replan_count == 0
        assert state.current_step_id is None
        assert state.execution_history == []
        assert state.observations == []
        assert state.errors == []
        assert state.metadata == {}

    def test_valid_with_runtime_data(self) -> None:
        state = make_agent_state(
            status=TaskStatus.EXECUTING,
            current_step_id="n1",
            retry_count=1,
            replan_count=2,
            observations=[Observation(source="tool", success=True)],
            errors=[make_error_record()],
        )
        assert state.status == TaskStatus.EXECUTING
        assert state.current_step_id == "n1"
        assert state.retry_count == 1
        assert state.replan_count == 2
        assert len(state.observations) == 1
        assert len(state.errors) == 1

    def test_with_execution_history(self) -> None:
        state = make_agent_state()
        step = ExecutionStep(
            step_number=1,
            node_id="n1",
            decision=make_decision_payload(),
            action="ran tool",
            observation={"source": "tool", "success": True, "data": {}},
            verification={"passed": True},
            duration_ms=10,
        )
        state.execution_history.append(step)
        assert len(state.execution_history) == 1

    def test_missing_request_fails(self) -> None:
        state = make_agent_state()
        with pytest.raises(ValidationError):
            AgentState(
                intent=state.intent,
                laya_classification=state.laya_classification,
                task_profile=state.task_profile,
                task_graph=state.task_graph,
            )

    def test_missing_task_graph_fails(self) -> None:
        with pytest.raises(ValidationError):
            AgentState(
                request=make_request(),
                intent=make_intent(),
                laya_classification=make_laya(),
                task_profile=make_profile(),
            )

    def test_negative_retry_count_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_agent_state(retry_count=-1)

    def test_negative_replan_count_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_agent_state(replan_count=-1)

    def test_extra_field_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_agent_state(max_retries=3)

    def test_invalid_status_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_agent_state(status="FLYING")

    def test_no_runtime_config_fields_duplicated(self) -> None:
        """AgentState must not carry RuntimeConfig limit fields."""
        fields = set(AgentState.model_fields.keys())
        for banned in ("max_retries", "max_replans", "global_timeout_ms"):
            assert banned not in fields, f"AgentState must not define {banned}"

    def test_no_execution_logic(self) -> None:
        """AgentState must not expose execution/decision behaviour."""
        for banned in ("execute", "decide", "plan", "run_tool", "next_decision"):
            assert not hasattr(AgentState, banned)

    def test_roundtrip(self) -> None:
        state = make_agent_state(status=TaskStatus.DECIDING, retry_count=2)
        state.execution_history.append(
            ExecutionStep(
                step_number=1,
                node_id="n1",
                decision=make_decision_payload(),
                action="ran tool",
                observation={"source": "tool", "success": True, "data": {}},
                verification={"passed": True},
                duration_ms=10,
            )
        )
        restored = AgentState.model_validate(state.model_dump(mode="json"))
        assert restored == state
        assert isinstance(restored.execution_history[0].decision, ExecuteDecision)


# ---------------------------------------------------------------------------
# Serialization round trips
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_every_decision_type_roundtrips(self) -> None:
        payloads = [
            make_decision_payload(),
            make_decision_payload(type="OBSERVE", parameters={"observation_target": "x"}),
            make_decision_payload(type="REPLAN", parameters={"replan_reason": "r"}),
            make_decision_payload(
                type="RETRY", parameters={"target_node_id": "n1", "retry_count": 1}
            ),
            make_decision_payload(type="ASK_USER", parameters={"question": "q"}),
            make_decision_payload(type="WAIT", parameters={"condition": "c", "timeout_ms": 5}),
            make_decision_payload(type="COMPLETE", parameters={"summary": "s"}),
            make_decision_payload(type="FAIL", parameters={"reason": "r"}),
        ]
        for payload in payloads:
            original = ADAPTER.validate_python(payload)
            dumped = original.model_dump(mode="json")
            restored = ADAPTER.validate_python(dumped)
            assert restored == original
            assert type(restored) is type(original)

    def test_dump_json_roundtrips(self) -> None:
        original = ADAPTER.validate_python(make_decision_payload())
        restored = ADAPTER.validate_json(original.model_dump_json())
        assert restored == original

    def test_decision_type_survives_serialization(self) -> None:
        original = ADAPTER.validate_python(
            make_decision_payload(type="FAIL", parameters={"reason": "x"})
        )
        assert original.model_dump(mode="json")["type"] == "FAIL"


# ---------------------------------------------------------------------------
# Generated JSON Schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_every_decision_validates_against_own_schema(self) -> None:
        schema_map = {
            "EXECUTE": "execute-decision.json",
            "OBSERVE": "observe-decision.json",
            "REPLAN": "replan-decision.json",
            "RETRY": "retry-decision.json",
            "ASK_USER": "ask-user-decision.json",
            "WAIT": "wait-decision.json",
            "COMPLETE": "complete-decision.json",
            "FAIL": "fail-decision.json",
        }
        payloads = {
            "EXECUTE": make_decision_payload(),
            "OBSERVE": make_decision_payload(type="OBSERVE", parameters={}),
            "REPLAN": make_decision_payload(type="REPLAN", parameters={"replan_reason": "r"}),
            "RETRY": make_decision_payload(
                type="RETRY", parameters={"target_node_id": "n1", "retry_count": 1}
            ),
            "ASK_USER": make_decision_payload(type="ASK_USER", parameters={"question": "q"}),
            "WAIT": make_decision_payload(
                type="WAIT", parameters={"condition": "c", "timeout_ms": 5}
            ),
            "COMPLETE": make_decision_payload(type="COMPLETE", parameters={}),
            "FAIL": make_decision_payload(type="FAIL", parameters={"reason": "r"}),
        }
        for decision_type, schema_name in schema_map.items():
            model = ADAPTER.validate_python(payloads[decision_type])
            jsonschema.validate(model.model_dump(mode="json"), load_schema(schema_name))

    def test_agent_state_validates_against_schema(self) -> None:
        state = make_agent_state(status=TaskStatus.EXECUTING, retry_count=1)
        jsonschema.validate(state.model_dump(mode="json"), load_schema("agent-state.json"))

    def test_execution_step_validates_against_schema(self) -> None:
        step = ExecutionStep(
            step_number=1,
            node_id="n1",
            decision=make_decision_payload(),
            action="a",
            observation={"source": "tool", "success": True, "data": {}},
            verification={"passed": True},
            duration_ms=1,
        )
        jsonschema.validate(step.model_dump(mode="json"), load_schema("execution-step.json"))

    def test_runtime_config_validates_against_schema(self) -> None:
        jsonschema.validate(RuntimeConfig().model_dump(mode="json"), load_schema("runtime-config.json"))

    def test_error_record_validates_against_schema(self) -> None:
        jsonschema.validate(
            make_error_record().model_dump(mode="json"), load_schema("error-record.json")
        )

    def test_observation_validates_against_schema(self) -> None:
        jsonschema.validate(
            Observation(source="tool", success=True).model_dump(mode="json"),
            load_schema("observation.json"),
        )


# ---------------------------------------------------------------------------
# Pydantic / schema alignment
# ---------------------------------------------------------------------------


class TestSchemaAlignment:
    def test_agent_state_required_fields(self) -> None:
        schema = load_schema("agent-state.json")
        assert set(schema["required"]) == {
            "request",
            "intent",
            "laya_classification",
            "task_profile",
            "task_graph",
        }

    def test_agent_state_optional_fields(self) -> None:
        schema = load_schema("agent-state.json")
        for optional in (
            "execution_history",
            "current_step_id",
            "status",
            "observations",
            "errors",
            "retry_count",
            "replan_count",
            "metadata",
        ):
            assert optional not in schema["required"]

    def test_agent_state_forbids_extra(self) -> None:
        assert load_schema("agent-state.json")["additionalProperties"] is False

    def test_execute_decision_required(self) -> None:
        schema = load_schema("execute-decision.json")
        assert set(schema["required"]) == {"id", "reasoning", "confidence", "parameters"}
        assert schema["$defs"]["ExecuteParams"]["required"] == ["target_node_id"]

    def test_retry_decision_params_required(self) -> None:
        schema = load_schema("retry-decision.json")
        assert set(schema["$defs"]["RetryParams"]["required"]) == {
            "target_node_id",
            "retry_count",
        }

    def test_decision_type_enum_schema(self) -> None:
        schema = load_schema("decision-type.json")
        assert schema["enum"] == [t.value for t in DecisionType]

    def test_task_status_enum_schema(self) -> None:
        schema = load_schema("task-status.json")
        assert schema["enum"] == [s.value for s in TaskStatus]

    def test_all_decision_schemas_forbid_extra(self) -> None:
        for name in (
            "execute-decision", "observe-decision", "replan-decision",
            "retry-decision", "ask-user-decision", "wait-decision",
            "complete-decision", "fail-decision",
        ):
            assert load_schema(f"{name}.json")["additionalProperties"] is False

    def test_agent_state_schema_matches_model(self) -> None:
        assert load_schema("agent-state.json") == AgentState.model_json_schema()

    def test_schemas_regenerate_identically(self) -> None:
        from jarvis.contracts.models.group_c import (
            ExecuteDecision, ObserveDecision, ReplanDecision, RetryDecision,
            AskUserDecision, WaitDecision, CompleteDecision, FailDecision,
        )
        pairs = [
            ("execute-decision", ExecuteDecision),
            ("observe-decision", ObserveDecision),
            ("replan-decision", ReplanDecision),
            ("retry-decision", RetryDecision),
            ("ask-user-decision", AskUserDecision),
            ("wait-decision", WaitDecision),
            ("complete-decision", CompleteDecision),
            ("fail-decision", FailDecision),
        ]
        for name, model in pairs:
            assert load_schema(f"{name}.json") == model.model_json_schema(), name

    def test_schema_files_exist(self) -> None:
        expected = [
            "agent-state.json", "runtime-config.json", "execution-step.json",
            "observation.json", "verification-result.json", "error-record.json",
            "execute-decision.json", "observe-decision.json", "replan-decision.json",
            "retry-decision.json", "ask-user-decision.json", "wait-decision.json",
            "complete-decision.json", "fail-decision.json",
            "execute-params.json", "observe-params.json", "replan-params.json",
            "retry-params.json", "ask-user-params.json", "wait-params.json",
            "complete-params.json", "fail-params.json",
            "decision-type.json", "task-status.json",
        ]
        for name in expected:
            assert (SCHEMA_DIR / name).exists(), f"Missing schema: {name}"


# ---------------------------------------------------------------------------
# Top-level Decision schema (schemas/decision.json)
# ---------------------------------------------------------------------------


DECISION_VARIANTS: dict[str, str] = {
    "EXECUTE": "ExecuteDecision",
    "OBSERVE": "ObserveDecision",
    "REPLAN": "ReplanDecision",
    "RETRY": "RetryDecision",
    "ASK_USER": "AskUserDecision",
    "WAIT": "WaitDecision",
    "COMPLETE": "CompleteDecision",
    "FAIL": "FailDecision",
}


class TestDecisionSchemaStructure:
    def test_decision_schema_exists(self) -> None:
        assert (SCHEMA_DIR / "decision.json").exists()

    def test_uses_one_of_with_eight_branches(self) -> None:
        schema = load_schema("decision.json")
        assert len(schema["oneOf"]) == 8

    def test_discriminator_is_on_type(self) -> None:
        schema = load_schema("decision.json")
        assert schema["discriminator"]["propertyName"] == "type"

    def test_discriminator_maps_exactly_the_eight_types(self) -> None:
        schema = load_schema("decision.json")
        mapping = schema["discriminator"]["mapping"]
        assert set(mapping) == set(DECISION_VARIANTS)

    def test_each_discriminator_entry_points_at_a_real_def(self) -> None:
        schema = load_schema("decision.json")
        defs = schema["$defs"]
        for type_name, ref in schema["discriminator"]["mapping"].items():
            assert ref.startswith("#/$defs/")
            assert ref.split("/")[-1] in defs, f"{type_name} -> {ref} has no $def"

    def test_one_of_branches_are_the_eight_variant_refs(self) -> None:
        schema = load_schema("decision.json")
        refs = {b["$ref"].split("/")[-1] for b in schema["oneOf"]}
        assert refs == set(DECISION_VARIANTS.values())

    def test_decision_schema_is_model_derived(self) -> None:
        assert load_schema("decision.json") == ADAPTER.json_schema()

    def test_decision_schema_regenerates_identically(self) -> None:
        """Guards against a hand-edited decision.json drifting from the models."""
        assert load_schema("decision.json") == ADAPTER.json_schema()


class TestDecisionSchemaValid:
    """The top-level schema accepts one valid instance of each decision type."""

    VALID: dict[str, dict] = {
        "EXECUTE": {"id": "d", "type": "EXECUTE", "reasoning": "go", "confidence": 0.9,
                    "parameters": {"target_node_id": "n1"}},
        "OBSERVE": {"id": "d", "type": "OBSERVE", "reasoning": "look", "confidence": 0.5,
                    "parameters": {}},
        "REPLAN": {"id": "d", "type": "REPLAN", "reasoning": "changed", "confidence": 0.5,
                   "parameters": {"replan_reason": "requirements changed"}},
        "RETRY": {"id": "d", "type": "RETRY", "reasoning": "again", "confidence": 0.5,
                  "parameters": {"target_node_id": "n1", "retry_count": 1}},
        "ASK_USER": {"id": "d", "type": "ASK_USER", "reasoning": "ask", "confidence": 0.5,
                     "parameters": {"question": "proceed?"}},
        "WAIT": {"id": "d", "type": "WAIT", "reasoning": "hold", "confidence": 0.5,
                 "parameters": {"condition": "file appears", "timeout_ms": 1000}},
        "COMPLETE": {"id": "d", "type": "COMPLETE", "reasoning": "done", "confidence": 1.0,
                     "parameters": {"summary": "all done", "result": {"ok": True}}},
        "FAIL": {"id": "d", "type": "FAIL", "reasoning": "stuck", "confidence": 1.0,
                 "parameters": {"reason": "unrecoverable"}},
    }

    def test_all_eight_types_covered(self) -> None:
        assert set(self.VALID) == set(DECISION_VARIANTS)

    @pytest.mark.parametrize("decision_type", sorted(DECISION_VARIANTS))
    def test_valid_instance_accepted(self, decision_type: str) -> None:
        jsonschema.validate(self.VALID[decision_type], load_schema("decision.json"))

    @pytest.mark.parametrize("decision_type", sorted(DECISION_VARIANTS))
    def test_pydantic_output_validates(self, decision_type: str) -> None:
        """Serialized output from the Pydantic model must satisfy the schema."""
        model = ADAPTER.validate_python(self.VALID[decision_type])
        jsonschema.validate(model.model_dump(mode="json"), load_schema("decision.json"))

    @pytest.mark.parametrize("decision_type", sorted(DECISION_VARIANTS))
    def test_pydantic_json_roundtrip_validates(self, decision_type: str) -> None:
        model = ADAPTER.validate_python(self.VALID[decision_type])
        reloaded = json.loads(model.model_dump_json())
        jsonschema.validate(reloaded, load_schema("decision.json"))


class TestDecisionSchemaInvalid:
    """The top-level schema rejects malformed and unknown decisions."""

    def test_unknown_decision_type_rejected(self) -> None:
        inst = {"id": "d", "type": "TELEPORT", "reasoning": "r", "confidence": 0.5,
                "parameters": {}}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(inst, load_schema("decision.json"))

    def test_missing_type_rejected(self) -> None:
        inst = {"id": "d", "reasoning": "r", "confidence": 0.5, "parameters": {}}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(inst, load_schema("decision.json"))

    def test_lowercase_type_rejected(self) -> None:
        inst = {"id": "d", "type": "execute", "reasoning": "r", "confidence": 0.5,
                "parameters": {"target_node_id": "n1"}}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(inst, load_schema("decision.json"))

    @pytest.mark.parametrize(
        "decision_type,params",
        [
            ("EXECUTE", {}),                                   # target_node_id required
            ("EXECUTE", {"tool_params": {}}),                  # still missing target_node_id
            ("OBSERVE", {"replan_reason": "x"}),               # field belongs to REPLAN
            ("REPLAN", {}),                                    # replan_reason required
            ("RETRY", {"target_node_id": "n1"}),               # retry_count required
            ("RETRY", {"retry_count": 1}),                     # target_node_id required
            ("RETRY", {"target_node_id": "n1", "retry_count": 0}),  # 1-indexed
            ("ASK_USER", {}),                                  # question required
            ("ASK_USER", {"options": ["a"]}),                  # still missing question
            ("WAIT", {"condition": "c"}),                      # timeout_ms required
            ("WAIT", {"timeout_ms": 1}),                       # condition required
            ("WAIT", {"condition": "c", "timeout_ms": 0}),     # must be >= 1
            ("FAIL", {}),                                      # reason required
            ("FAIL", {"error": {"code": "E", "message": "m", "recoverable": False}}),
            ("COMPLETE", {"score": 1}),                        # unknown field
            ("EXECUTE", {"target_node_id": "n1", "junk": 1}),  # unknown field
        ],
    )
    def test_malformed_params_rejected(self, decision_type: str, params: dict) -> None:
        inst = {"id": "d", "type": decision_type, "reasoning": "r",
                "confidence": 0.5, "parameters": params}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(inst, load_schema("decision.json"))

    def test_extra_top_level_field_rejected(self) -> None:
        inst = {"id": "d", "type": "EXECUTE", "reasoning": "r", "confidence": 0.5,
                "parameters": {"target_node_id": "n1"}, "junk": 1}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(inst, load_schema("decision.json"))

    def test_missing_required_base_fields_rejected(self) -> None:
        for missing in ("id", "reasoning", "confidence", "parameters"):
            inst = {"id": "d", "type": "EXECUTE", "reasoning": "r", "confidence": 0.5,
                    "parameters": {"target_node_id": "n1"}}
            del inst[missing]
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate(inst, load_schema("decision.json"))

    def test_confidence_out_of_range_rejected(self) -> None:
        for bad in (-0.1, 1.1):
            inst = {"id": "d", "type": "EXECUTE", "reasoning": "r", "confidence": bad,
                    "parameters": {"target_node_id": "n1"}}
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate(inst, load_schema("decision.json"))

    def test_parameters_not_an_object_rejected(self) -> None:
        inst = {"id": "d", "type": "EXECUTE", "reasoning": "r", "confidence": 0.5,
                "parameters": "nope"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(inst, load_schema("decision.json"))


# ---------------------------------------------------------------------------
# Documented invariants (ADR 04 / ADR 06)
# ---------------------------------------------------------------------------


class TestDocumentedInvariants:
    def test_unsuccessful_observation_requires_error(self) -> None:
        """ADR 04: `error: ErrorRecord // Error details if not successful`."""
        with pytest.raises(ValidationError):
            Observation(source="tool", data={}, success=False)

    def test_successful_observation_may_omit_error(self) -> None:
        assert Observation(source="tool", success=True).error is None

    def test_retry_count_must_be_at_least_one(self) -> None:
        """ADR 06: retry_count is 1-indexed, so 0 is not a valid attempt."""
        with pytest.raises(ValidationError):
            RetryParams(target_node_id="n1", retry_count=0)

    def test_retry_count_one_is_accepted(self) -> None:
        assert RetryParams(target_node_id="n1", retry_count=1).retry_count == 1

    def test_agent_state_retry_count_is_authoritative_counter(self) -> None:
        """ADR 04: Orchestrator increments AgentState.retry_count per RETRY."""
        state = make_agent_state()
        assert state.retry_count == 0
        state.retry_count += 1
        assert state.retry_count == 1

    def test_agent_state_replan_count_is_authoritative_counter(self) -> None:
        """ADR 04: Orchestrator increments AgentState.replan_count per REPLAN."""
        state = make_agent_state()
        assert state.replan_count == 0
        state.replan_count += 1
        assert state.replan_count == 1

    def test_runtime_config_is_separate_from_agent_state(self) -> None:
        """ADR 04: RuntimeConfig holds limits; AgentState holds counters."""
        state_fields = set(AgentState.model_fields)
        config_fields = set(RuntimeConfig.model_fields)
        assert state_fields.isdisjoint(config_fields)
        assert {"max_retries", "max_replans"} <= config_fields
        assert {"retry_count", "replan_count"} <= state_fields

    def test_counters_and_limits_compose(self) -> None:
        """The comparison the Orchestrator must make is expressible."""
        cfg = RuntimeConfig(max_retries=3, max_replans=2)
        state = make_agent_state(retry_count=3, replan_count=2)
        assert state.retry_count >= cfg.max_retries
        assert state.replan_count >= cfg.max_replans

    def test_decision_retry_count_is_not_trusted_over_agent_state(self) -> None:
        """ADR 06: Decision.retry_count is advisory; no consistency rule exists."""
        decision = ADAPTER.validate_python(
            make_decision_payload(
                type="RETRY",
                retry_count=99,
                parameters={"target_node_id": "n1", "retry_count": 1},
            )
        )
        state = make_agent_state(retry_count=0)
        assert decision.retry_count != state.retry_count  # no rejection, no reconciliation
