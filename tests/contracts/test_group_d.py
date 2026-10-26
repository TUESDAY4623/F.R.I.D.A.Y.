"""Tests for Group D contracts: Execution boundary layer."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError as PydValidationError

from jarvis.contracts.models.group_a import (
    Intent,
    LayaCategory,
    LayaClassification,
    Request,
)
from jarvis.contracts.models.group_b import TaskGraph, TaskGraphNode, TaskProfile
from jarvis.contracts.models.group_c import AgentState, ErrorRecord
from jarvis.contracts.models.group_d import (
    PolicyResult,
    ProposedAction,
    ToolResult,
    ValidationError_,
    ValidationResult,
)

SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_schema(name: str) -> dict:
    path = SCHEMA_DIR / name
    assert path.exists(), f"Schema file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_agent_state(**overrides: Any) -> AgentState:
    request = Request(id="req-1", raw_input="do it", normalized_input="do it")
    laya = LayaClassification(
        request_id="req-1",
        category=LayaCategory.ACTIONABLE,
        confidence=0.9,
        ambiguous=False,
    )
    intent = Intent(
        request_id="req-1",
        laya_category=LayaCategory.ACTIONABLE,
        normalized_form="do it",
        confidence=0.9,
        ambiguous=False,
    )
    profile = TaskProfile(
        intent_id="req-1",
        task_type="single-step",
        complexity="low",
        estimated_steps=1,
    )
    node = TaskGraphNode(id="n1", type="tool_call", description="step", expected_outcome="done")
    graph = TaskGraph(id="g1", nodes=[node], edges=[], entry_node_id="n1")
    data: dict[str, Any] = {
        "request": request,
        "intent": intent,
        "laya_classification": laya,
        "task_profile": profile,
        "task_graph": graph,
    }
    data.update(overrides)
    return AgentState(**data)


def make_proposed_action(**overrides: Any) -> ProposedAction:
    data: dict[str, Any] = {
        "action_type": "tool_call",
        "tool_name": "mock_tool",
        "parameters": {"arg": 1},
        "agent_state": make_agent_state(),
        "task_graph_node_id": "n1",
    }
    data.update(overrides)
    return ProposedAction(**data)


def make_tool_result(**overrides: Any) -> ToolResult:
    data: dict[str, Any] = {
        "success": True,
        "duration_ms": 12,
    }
    data.update(overrides)
    return ToolResult(**data)


# ---------------------------------------------------------------------------
# ValidationError
# ---------------------------------------------------------------------------


class TestValidationError:
    def test_valid_minimal(self) -> None:
        e = ValidationError_(field="x", message="bad value", code="FIELD_001")
        assert e.field == "x"
        assert e.code == "FIELD_001"

    def test_empty_field_fails(self) -> None:
        with pytest.raises(PydValidationError):
            ValidationError_(field="", message="m", code="c")

    def test_empty_message_fails(self) -> None:
        with pytest.raises(PydValidationError):
            ValidationError_(field="f", message="  ", code="c")

    def test_empty_code_fails(self) -> None:
        with pytest.raises(PydValidationError):
            ValidationError_(field="f", message="m", code="")

    def test_extra_field_fails(self) -> None:
        with pytest.raises(PydValidationError):
            ValidationError_(field="f", message="m", code="c", extra="x")

    def test_schema_title_is_validation_error(self) -> None:
        schema = load_schema("validation-error.json")
        assert schema["title"] == "ValidationError"

    def test_roundtrip(self) -> None:
        e = ValidationError_(field="f", message="m", code="c")
        assert ValidationError_.model_validate(e.model_dump(mode="json")) == e


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_valid_no_errors(self) -> None:
        v = ValidationResult(valid=True)
        assert v.valid is True
        assert v.errors == []
        assert v.warnings == []

    def test_valid_with_warnings(self) -> None:
        v = ValidationResult(valid=True, warnings=["note"])
        assert len(v.warnings) == 1

    def test_invalid_with_errors(self) -> None:
        err = ValidationError_(field="x", message="bad", code="E1")
        v = ValidationResult(valid=False, errors=[err])
        assert len(v.errors) == 1
        assert isinstance(v.errors[0], ValidationError_)

    def test_valid_with_errors_rejected(self) -> None:
        err = ValidationError_(field="x", message="bad", code="E1")
        with pytest.raises(PydValidationError):
            ValidationResult(valid=True, errors=[err])

    def test_invalid_without_errors_rejected(self) -> None:
        with pytest.raises(PydValidationError):
            ValidationResult(valid=False)

    def test_invalid_with_warnings_rejected(self) -> None:
        # warnings are non-blocking but errors must still be present when invalid
        with pytest.raises(PydValidationError):
            ValidationResult(valid=False, warnings=["note"])

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(PydValidationError):
            ValidationResult(valid=True, unknown="x")

    def test_roundtrip(self) -> None:
        err = ValidationError_(field="f", message="m", code="c")
        v = ValidationResult(valid=False, errors=[err])
        restored = ValidationResult.model_validate(v.model_dump(mode="json"))
        assert restored == v

    def test_schema_valid(self) -> None:
        v = ValidationResult(valid=True)
        jsonschema.validate(v.model_dump(mode="json"), load_schema("validation-result.json"))

    def test_schema_valid_shape_accepted(self) -> None:
        """Schema enforces structural shape; the cross-field invariant
        (errors empty iff valid) is enforced by the Pydantic model, not
        by JSON Schema. Confirm the schema accepts a structurally valid
        instance and rejects a structurally invalid one."""
        good = {"valid": True, "errors": [], "warnings": []}
        jsonschema.validate(good, load_schema("validation-result.json"))

        bad_missing_field = {"valid": True}  # errors/warnings omitted — schema allows (defaults)
        jsonschema.validate(bad_missing_field, load_schema("validation-result.json"))

        bad_extra_field = {"valid": True, "errors": [], "warnings": [], "unknown": 1}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad_extra_field, load_schema("validation-result.json"))

    def test_schema_required_is_valid_only(self) -> None:
        """Confirm the schema marks only `valid` as required — errors and
        warnings have defaults and are not required at the schema level."""
        schema = load_schema("validation-result.json")
        assert schema["required"] == ["valid"]


# ---------------------------------------------------------------------------
# ProposedAction
# ---------------------------------------------------------------------------


class TestProposedAction:
    def test_valid_minimal(self) -> None:
        a = make_proposed_action()
        assert a.action_type == "tool_call"
        assert a.tool_name == "mock_tool"
        assert a.task_graph_node_id == "n1"
        assert isinstance(a.agent_state, AgentState)
        assert a.parameters == {"arg": 1}
        assert isinstance(a.timestamp, datetime)

    def test_timestamp_defaults_to_utc_now(self) -> None:
        a = make_proposed_action()
        assert a.timestamp.tzinfo is not None
        assert a.timestamp.tzinfo == timezone.utc

    def test_timestamp_explicit_value_preserved(self) -> None:
        ts = datetime.now(timezone.utc)
        a = make_proposed_action(timestamp=ts)
        assert a.timestamp == ts

    def test_missing_action_type_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_proposed_action(action_type="")

    def test_missing_tool_name_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_proposed_action(tool_name="")

    def test_missing_task_graph_node_id_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_proposed_action(task_graph_node_id="")

    def test_missing_agent_state_fails(self) -> None:
        with pytest.raises(PydValidationError):
            ProposedAction(
                action_type="tool_call",
                tool_name="mock_tool",
                task_graph_node_id="n1",
            )

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(PydValidationError):
            make_proposed_action(unknown="x")

    def test_parameters_default_to_empty_dict(self) -> None:
        a = make_proposed_action(parameters={})
        assert a.parameters == {}

    def test_roundtrip(self) -> None:
        a = make_proposed_action()
        restored = ProposedAction.model_validate(a.model_dump(mode="json"))
        assert restored.action_type == a.action_type
        assert restored.tool_name == a.tool_name
        assert restored.task_graph_node_id == a.task_graph_node_id
        assert isinstance(restored.agent_state, AgentState)

    def test_schema_valid(self) -> None:
        a = make_proposed_action()
        jsonschema.validate(a.model_dump(mode="json"), load_schema("proposed-action.json"))

    def test_schema_requires_agent_state(self) -> None:
        schema = load_schema("proposed-action.json")
        assert "agent_state" in schema["required"]

    def test_schema_timestamp_optional_with_default(self) -> None:
        schema = load_schema("proposed-action.json")
        # timestamp has a default (utc_now), so it must not be required,
        # but the property itself must be present.
        assert "timestamp" not in schema["required"]
        ts = schema["properties"]["timestamp"]
        assert ts.get("format") == "date-time"
        assert "anyOf" not in ts  # not nullable — a concrete default, not null


# ---------------------------------------------------------------------------
# PolicyResult
# ---------------------------------------------------------------------------


class TestPolicyResult:
    def test_approved_with_token(self) -> None:
        p = PolicyResult(
            approved=True,
            reason="ok",
            approval_token="tok-123",
        )
        assert p.approved is True
        assert p.approval_token == "tok-123"
        assert p.conditions == []
        assert p.rule_triggers == []

    def test_denied_without_token(self) -> None:
        p = PolicyResult(
            approved=False,
            reason="blocked by rule",
            rule_triggers=["no-external-network"],
        )
        assert p.approved is False
        assert p.approval_token is None

    def test_approved_without_token_rejected(self) -> None:
        with pytest.raises(PydValidationError):
            PolicyResult(approved=True, reason="ok")

    def test_denied_with_token_rejected(self) -> None:
        with pytest.raises(PydValidationError):
            PolicyResult(approved=False, reason="no", approval_token="tok")

    def test_empty_reason_rejected(self) -> None:
        with pytest.raises(PydValidationError):
            PolicyResult(approved=True, reason="", approval_token="t")

    def test_empty_token_rejected(self) -> None:
        with pytest.raises(PydValidationError):
            PolicyResult(approved=True, reason="ok", approval_token="")

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(PydValidationError):
            PolicyResult(approved=True, reason="ok", approval_token="t", junk=1)

    def test_roundtrip_approved(self) -> None:
        p = PolicyResult(
            approved=True,
            reason="ok",
            conditions=["read-only"],
            rule_triggers=["rate-limit"],
            approval_token="tok",
        )
        restored = PolicyResult.model_validate(p.model_dump(mode="json"))
        assert restored == p

    def test_roundtrip_denied(self) -> None:
        p = PolicyResult(
            approved=False,
            reason="denied",
            rule_triggers=["deny-rule"],
        )
        restored = PolicyResult.model_validate(p.model_dump(mode="json"))
        assert restored == p

    def test_schema_valid(self) -> None:
        p = PolicyResult(approved=True, reason="ok", approval_token="tok")
        jsonschema.validate(p.model_dump(mode="json"), load_schema("policy-result.json"))

    def test_schema_denied_valid(self) -> None:
        p = PolicyResult(approved=False, reason="nope", rule_triggers=["r1"])
        jsonschema.validate(p.model_dump(mode="json"), load_schema("policy-result.json"))


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------


def make_error_record(**overrides: Any) -> ErrorRecord:
    data: dict[str, Any] = {
        "code": "TOOL_001",
        "message": "boom",
        "recoverable": False,
    }
    data.update(overrides)
    return ErrorRecord(**data)


class TestToolResult:
    def test_valid_success(self) -> None:
        r = make_tool_result(data={"rows": 3})
        assert r.success is True
        assert r.data == {"rows": 3}
        assert r.error is None
        assert r.metadata == {}
        assert r.duration_ms == 12

    def test_valid_failure_with_error(self) -> None:
        r = make_tool_result(
            success=False,
            error=make_error_record(),
            data={},
        )
        assert r.success is False
        assert isinstance(r.error, ErrorRecord)
        assert r.error.code == "TOOL_001"
        assert r.data == {}

    def test_missing_success_fails(self) -> None:
        with pytest.raises(PydValidationError):
            ToolResult(duration_ms=5)

    def test_missing_duration_ms_fails(self) -> None:
        with pytest.raises(PydValidationError):
            ToolResult(success=True)

    def test_invalid_success_type_fails(self) -> None:
        # non-bool values that cannot be coerced to bool are rejected
        for bad in (1.5, {"a": 1}, [1]):
            with pytest.raises(PydValidationError):
                make_tool_result(success=bad)

    def test_invalid_data_type_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_tool_result(data=[1, 2])

    def test_invalid_error_type_fails(self) -> None:
        # error must be an ErrorRecord (or None when success). A dict is
        # coerced to an ErrorRecord, but a plain string / int / list is not.
        for bad in ("not-an-error-record", 42, [1, 2]):
            with pytest.raises(PydValidationError):
                ToolResult(
                    success=False,
                    error=bad,
                    duration_ms=5,
                )

    def test_invalid_metadata_type_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_tool_result(metadata=["not", "a", "dict"])

    def test_negative_duration_ms_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_tool_result(duration_ms=-1)

    def test_zero_duration_ms_is_valid(self) -> None:
        # ADR 07 only says "Execution duration" — ge=0 permits a zero-duration result
        r = make_tool_result(duration_ms=0)
        assert r.duration_ms == 0

    def test_failed_without_error_rejected(self) -> None:
        """ADR 07 / Observation convention: a failed result must carry an error."""
        with pytest.raises(PydValidationError):
            ToolResult(success=False, duration_ms=5)

    def test_success_with_error_is_allowed(self) -> None:
        """The invariant is one-directional: a successful result may still carry
        an error (mirrors Observation, which enforces only the failure direction)."""
        r = ToolResult(success=True, error=make_error_record(), duration_ms=5)
        assert r.success is True
        assert r.error is not None

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(PydValidationError):
            make_tool_result(junk=1)

    def test_roundtrip_success(self) -> None:
        r = make_tool_result(data={"k": "v"}, metadata={"tool": "mock"})
        restored = ToolResult.model_validate(r.model_dump(mode="json"))
        assert restored == r

    def test_roundtrip_failure(self) -> None:
        r = make_tool_result(success=False, error=make_error_record())
        restored = ToolResult.model_validate(r.model_dump(mode="json"))
        assert restored.success is False
        assert isinstance(restored.error, ErrorRecord)
        assert restored.error.code == r.error.code

    def test_dump_json_roundtrip(self) -> None:
        r = make_tool_result()
        restored = ToolResult.model_validate_json(r.model_dump_json())
        assert restored == r

    def test_schema_valid_success(self) -> None:
        r = make_tool_result(data={"x": 1})
        jsonschema.validate(r.model_dump(mode="json"), load_schema("tool-result.json"))

    def test_schema_valid_failure(self) -> None:
        r = make_tool_result(success=False, error=make_error_record())
        jsonschema.validate(r.model_dump(mode="json"), load_schema("tool-result.json"))

    def test_schema_alignment_with_model(self) -> None:
        assert load_schema("tool-result.json") == ToolResult.model_json_schema()

    def test_schema_determinism(self) -> None:
        """Two independent schema generations produce identical output."""
        assert ToolResult.model_json_schema() == ToolResult.model_json_schema()

    def test_schema_failure_shape_rejected(self) -> None:
        """A structurally valid dict missing the required `success` field is
        rejected by the generated schema."""
        bad = {"data": {}, "duration_ms": 5}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, load_schema("tool-result.json"))


# ---------------------------------------------------------------------------
# Schema structural checks
# ---------------------------------------------------------------------------


class TestSchemaAlignment:
    def test_validation_result_required(self) -> None:
        schema = load_schema("validation-result.json")
        assert "valid" in schema["required"]

    def test_validation_error_title(self) -> None:
        schema = load_schema("validation-error.json")
        assert schema["title"] == "ValidationError"

    def test_proposed_action_required(self) -> None:
        schema = load_schema("proposed-action.json")
        for field in ("action_type", "tool_name", "agent_state", "task_graph_node_id"):
            assert field in schema["required"], f"missing {field}"

    def test_policy_result_required(self) -> None:
        schema = load_schema("policy-result.json")
        for field in ("approved", "reason"):
            assert field in schema["required"], f"missing {field}"

    def test_tool_result_required(self) -> None:
        schema = load_schema("tool-result.json")
        for field in ("success", "duration_ms"):
            assert field in schema["required"], f"missing {field}"
        # data / error / metadata are optional (defaults)
        for field in ("data", "error", "metadata"):
            assert field not in schema["required"], f"{field} should be optional"

    def test_all_schemas_forbid_extra(self) -> None:
        for name in ("validation-error", "validation-result", "proposed-action", "policy-result", "tool-result"):
            assert load_schema(f"{name}.json")["additionalProperties"] is False

    def test_schemas_regenerate_identically(self) -> None:
        pairs = [
            ("validation-error", ValidationError_),
            ("validation-result", ValidationResult),
            ("proposed-action", ProposedAction),
            ("policy-result", PolicyResult),
            ("tool-result", ToolResult),
        ]
        for name, model in pairs:
            assert load_schema(f"{name}.json") == model.model_json_schema(), name

    def test_schema_files_exist(self) -> None:
        for name in (
            "validation-error.json",
            "validation-result.json",
            "proposed-action.json",
            "policy-result.json",
            "tool-result.json",
        ):
            assert (SCHEMA_DIR / name).exists(), f"Missing schema: {name}"

    def test_no_observation_duplicate(self) -> None:
        """Group D must reuse group_c's Observation, not define a new one."""
        import jarvis.contracts.models.group_d as gd
        assert not hasattr(gd, "Observation"), "Group D must not redefine Observation"
