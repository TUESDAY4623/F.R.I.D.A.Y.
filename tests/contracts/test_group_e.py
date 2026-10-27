"""Tests for Group E contracts: User Interaction layer."""

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError as PydValidationError

from jarvis.contracts import UserResponse as TopLevelUserResponse
from jarvis.contracts.models.group_e import (
    UserResponse,
    WaitCondition,
    WaitConditionType,
)
from jarvis.contracts import WaitCondition as TopLevelWaitCondition
from jarvis.contracts import WaitConditionType as TopLevelWaitConditionType

SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"


def load_schema(name: str) -> dict:
    path = SCHEMA_DIR / name
    assert path.exists(), f"Schema file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_user_response(**overrides: Any) -> UserResponse:
    data: dict[str, Any] = {
        "response_id": "ask-1",
        "task_id": "task-1",
        "answer": "yes",
        "confirmed": True,
    }
    data.update(overrides)
    return UserResponse(**data)


def make_wait_condition(**overrides: Any) -> WaitCondition:
    data: dict[str, Any] = {
        "description": "Wait for file to appear",
        "condition_type": "file_presence",
        "timeout_ms": 60_000,
        "poll_interval_ms": 1_000,
    }
    data.update(overrides)
    return WaitCondition(**data)


# ---------------------------------------------------------------------------
# WaitConditionType enum
# ---------------------------------------------------------------------------


class TestWaitConditionType:
    def test_all_documented_values(self) -> None:
        assert [t.value for t in WaitConditionType] == [
            "file_presence",
            "process_start",
            "time_delay",
            "external_event",
        ]

    def test_schema_matches_enum(self) -> None:
        schema = load_schema("wait-condition-type.json")
        assert schema["enum"] == [t.value for t in WaitConditionType]


# ---------------------------------------------------------------------------
# UserResponse — valid cases
# ---------------------------------------------------------------------------


class TestUserResponseValid:
    def test_minimal(self) -> None:
        r = make_user_response()
        assert r.response_id == "ask-1"
        assert r.task_id == "task-1"
        assert r.answer == "yes"
        assert r.selected_option is None
        assert r.confirmed is True

    def test_with_selected_option(self) -> None:
        r = make_user_response(selected_option="option-a")
        assert r.selected_option == "option-a"

    def test_declined(self) -> None:
        r = make_user_response(confirmed=False, answer="no")
        assert r.confirmed is False

    def test_empty_options_list_is_implicit(self) -> None:
        """No selected_option provided means None — no assertion needed."""
        r = make_user_response()
        assert r.selected_option is None

    def test_timestamp_has_default(self) -> None:
        r = make_user_response()
        assert r.timestamp is not None


# ---------------------------------------------------------------------------
# UserResponse — invalid cases
# ---------------------------------------------------------------------------


class TestUserResponseInvalid:
    def test_missing_response_id_fails(self) -> None:
        with pytest.raises(PydValidationError):
            UserResponse(task_id="t", answer="a", confirmed=True)

    def test_missing_task_id_fails(self) -> None:
        with pytest.raises(PydValidationError):
            UserResponse(response_id="r", answer="a", confirmed=True)

    def test_missing_answer_fails(self) -> None:
        with pytest.raises(PydValidationError):
            UserResponse(response_id="r", task_id="t", confirmed=True)

    def test_missing_confirmed_fails(self) -> None:
        with pytest.raises(PydValidationError):
            UserResponse(response_id="r", task_id="t", answer="a")

    def test_empty_response_id_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_user_response(response_id="")

    def test_empty_task_id_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_user_response(task_id="")

    def test_empty_answer_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_user_response(answer="")

    def test_extra_field_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_user_response(unknown="x")


# ---------------------------------------------------------------------------
# UserResponse — serialization and schema
# ---------------------------------------------------------------------------


class TestUserResponseSerialization:
    def test_roundtrip(self) -> None:
        r = make_user_response(selected_option="opt-1")
        restored = UserResponse.model_validate(r.model_dump(mode="json"))
        assert restored == r

    def test_dump_json_roundtrip(self) -> None:
        r = make_user_response()
        restored = UserResponse.model_validate_json(r.model_dump_json())
        assert restored == r

    def test_validates_against_schema(self) -> None:
        r = make_user_response(selected_option="opt-1")
        jsonschema.validate(r.model_dump(mode="json"), load_schema("user-response.json"))

    def test_schema_required_fields(self) -> None:
        schema = load_schema("user-response.json")
        assert set(schema["required"]) == {
            "response_id",
            "task_id",
            "answer",
            "confirmed",
        }

    def test_schema_forbids_extra(self) -> None:
        assert load_schema("user-response.json")["additionalProperties"] is False

    def test_schema_matches_model(self) -> None:
        assert load_schema("user-response.json") == UserResponse.model_json_schema()


# ---------------------------------------------------------------------------
# WaitCondition — valid cases
# ---------------------------------------------------------------------------


class TestWaitConditionValid:
    def test_minimal(self) -> None:
        w = make_wait_condition()
        assert w.description == "Wait for file to appear"
        assert w.condition_type == WaitConditionType.FILE_PRESENCE
        assert w.parameters == {}
        assert w.timeout_ms == 60_000
        assert w.poll_interval_ms == 1_000

    def test_with_parameters(self) -> None:
        w = make_wait_condition(
            condition_type="file_presence",
            parameters={"path": "/tmp/x"},
        )
        assert w.parameters == {"path": "/tmp/x"}

    def test_time_delay(self) -> None:
        w = make_wait_condition(
            condition_type="time_delay",
            parameters={"delay_ms": 5_000},
            timeout_ms=10_000,
            poll_interval_ms=500,
        )
        assert w.condition_type == WaitConditionType.TIME_DELAY

    def test_external_event(self) -> None:
        w = make_wait_condition(
            condition_type="external_event",
            parameters={"event": "build_complete"},
        )
        assert w.condition_type == WaitConditionType.EXTERNAL_EVENT

    def test_parameters_omitted_defaults_to_empty(self) -> None:
        """Decision B: omitting parameters defaults to {}."""
        w = WaitCondition(
            description="d",
            condition_type="file_presence",
            timeout_ms=100,
            poll_interval_ms=10,
        )
        assert w.parameters == {}

    def test_explicitly_empty_parameters_valid(self) -> None:
        """Decision B: an explicitly supplied empty object is valid."""
        w = WaitCondition(
            description="d",
            condition_type="time_delay",
            timeout_ms=100,
            poll_interval_ms=10,
            parameters={},
        )
        assert w.parameters == {}


# ---------------------------------------------------------------------------
# WaitCondition — invalid cases
# ---------------------------------------------------------------------------


class TestWaitConditionInvalid:
    def test_missing_description_fails(self) -> None:
        with pytest.raises(PydValidationError):
            WaitCondition(
                condition_type="file_presence",
                timeout_ms=100,
                poll_interval_ms=10,
            )

    def test_missing_condition_type_fails(self) -> None:
        with pytest.raises(PydValidationError):
            WaitCondition(description="d", timeout_ms=100, poll_interval_ms=10)

    def test_missing_timeout_fails(self) -> None:
        with pytest.raises(PydValidationError):
            WaitCondition(description="d", condition_type="file_presence", poll_interval_ms=10)

    def test_missing_poll_interval_fails(self) -> None:
        with pytest.raises(PydValidationError):
            WaitCondition(description="d", condition_type="file_presence", timeout_ms=100)

    def test_zero_timeout_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_wait_condition(timeout_ms=0)

    def test_zero_poll_interval_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_wait_condition(poll_interval_ms=0)

    def test_negative_poll_interval_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_wait_condition(poll_interval_ms=-1)

    def test_none_poll_interval_fails(self) -> None:
        """Decision A: poll_interval_ms must not be nullable."""
        with pytest.raises(PydValidationError):
            make_wait_condition(poll_interval_ms=None)

    def test_non_integer_poll_interval_fails(self) -> None:
        """A float is not a positive integer — rejected."""
        with pytest.raises(PydValidationError):
            make_wait_condition(poll_interval_ms=1.5)

    def test_parameters_must_be_dict(self) -> None:
        """Decision B: parameters container must be a mapping."""
        for bad in ([1, 2], None):
            with pytest.raises(PydValidationError):
                make_wait_condition(parameters=bad)

    def test_invalid_condition_type_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_wait_condition(condition_type="unknown_type")

    def test_empty_description_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_wait_condition(description="")

    def test_extra_field_fails(self) -> None:
        with pytest.raises(PydValidationError):
            make_wait_condition(unknown="x")


# ---------------------------------------------------------------------------
# WaitCondition — serialization and schema
# ---------------------------------------------------------------------------


class TestWaitConditionSerialization:
    def test_roundtrip(self) -> None:
        w = make_wait_condition(parameters={"key": "val"})
        restored = WaitCondition.model_validate(w.model_dump(mode="json"))
        assert restored == w

    def test_dump_json_roundtrip(self) -> None:
        w = make_wait_condition()
        restored = WaitCondition.model_validate_json(w.model_dump_json())
        assert restored == w

    def test_validates_against_schema(self) -> None:
        w = make_wait_condition(parameters={"path": "/x"})
        jsonschema.validate(w.model_dump(mode="json"), load_schema("wait-condition.json"))

    def test_schema_required_fields(self) -> None:
        """poll_interval_ms and timeout_ms are required; parameters is not."""
        schema = load_schema("wait-condition.json")
        assert set(schema["required"]) == {
            "description",
            "condition_type",
            "timeout_ms",
            "poll_interval_ms",
        }
        assert "parameters" not in schema["required"]

    def test_schema_poll_interval_ms_non_null(self) -> None:
        """Decision A: poll_interval_ms must not accept null in the schema."""
        schema = load_schema("wait-condition.json")
        poll = schema["properties"]["poll_interval_ms"]
        assert "null" not in poll.get("type", "single-value type")
        assert poll.get("type") == "integer"

    def test_schema_parameters_is_object(self) -> None:
        """Decision B: parameters must be an object type, optional."""
        schema = load_schema("wait-condition.json")
        params = schema["properties"]["parameters"]
        assert params["type"] == "object"

    def test_schema_rejects_missing_poll_interval(self) -> None:
        """Schema validation rejects an instance missing poll_interval_ms."""
        bad = {
            "description": "d",
            "condition_type": "file_presence",
            "parameters": {},
            "timeout_ms": 100,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, load_schema("wait-condition.json"))

    def test_schema_rejects_null_poll_interval(self) -> None:
        bad = {
            "description": "d",
            "condition_type": "file_presence",
            "parameters": {},
            "timeout_ms": 100,
            "poll_interval_ms": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, load_schema("wait-condition.json"))

    def test_schema_accepts_omitted_parameters(self) -> None:
        """Decision B: parameters may be absent from an instance."""
        inst = {
            "description": "d",
            "condition_type": "file_presence",
            "timeout_ms": 100,
            "poll_interval_ms": 10,
        }
        jsonschema.validate(inst, load_schema("wait-condition.json"))

    def test_schema_forbids_extra(self) -> None:
        assert load_schema("wait-condition.json")["additionalProperties"] is False

    def test_schema_condition_type_is_enum(self) -> None:
        schema = load_schema("wait-condition.json")
        ct_schema = schema["$defs"]["WaitConditionType"]
        assert ct_schema["enum"] == [
            "file_presence",
            "process_start",
            "time_delay",
            "external_event",
        ]

    def test_schema_matches_model(self) -> None:
        assert load_schema("wait-condition.json") == WaitCondition.model_json_schema()


# ---------------------------------------------------------------------------
# Export surface — top-level jarvis.contracts package
# ---------------------------------------------------------------------------


class TestTopLevelExports:
    """Group E contracts must be importable from the top-level package."""

    def test_user_response_exported(self) -> None:
        assert TopLevelUserResponse is UserResponse

    def test_wait_condition_exported(self) -> None:
        assert TopLevelWaitCondition is WaitCondition

    def test_wait_condition_type_exported(self) -> None:
        assert TopLevelWaitConditionType is WaitConditionType
