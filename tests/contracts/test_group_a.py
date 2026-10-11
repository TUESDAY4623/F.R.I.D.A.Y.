"""Tests for Group A contracts: Input & Intent layer."""

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from jarvis.contracts.models.group_a import (
    EntityType,
    ExtractedEntity,
    Intent,
    LayaCategory,
    LayaClassification,
    Request,
    RequestCharacteristic,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_request(
    request_id: str = "req-001",
    raw_input: str = "Open the file",
    normalized_input: str = "open the file",
    timestamp: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> Request:
    return Request(
        id=request_id,
        raw_input=raw_input,
        normalized_input=normalized_input,
        timestamp=timestamp or utc_now(),
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Request tests
# ---------------------------------------------------------------------------


class TestRequest:
    def test_valid(self) -> None:
        r = make_request()
        assert r.id == "req-001"
        assert r.raw_input == "Open the file"
        assert r.normalized_input == "open the file"
        assert isinstance(r.timestamp, datetime)
        assert r.metadata == {}

    def test_with_metadata(self) -> None:
        r = make_request(metadata={"source": "cli"})
        assert r.metadata == {"source": "cli"}

    def test_empty_raw_input_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_request(raw_input="")

    def test_whitespace_raw_input_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_request(raw_input="   ")

    def test_empty_normalized_input_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_request(normalized_input="")

    def test_serialize_roundtrip(self) -> None:
        r = make_request(request_id="req-abc")
        data = r.model_dump(mode="json")
        r2 = Request.model_validate(data)
        assert r2.id == "req-abc"


# ---------------------------------------------------------------------------
# ExtractedEntity tests
# ---------------------------------------------------------------------------


class TestExtractedEntity:
    def test_valid(self) -> None:
        e = ExtractedEntity(
            type=EntityType.FILE_PATH,
            value="/home/user/file.txt",
            confidence=0.95,
            context="opening file.txt",
        )
        assert e.type == EntityType.FILE_PATH
        assert e.value == "/home/user/file.txt"
        assert e.confidence == 0.95

    def test_confidence_min(self) -> None:
        e = ExtractedEntity(
            type=EntityType.APP_NAME,
            value="notepad",
            confidence=0.0,
            context="open notepad",
        )
        assert e.confidence == 0.0

    def test_confidence_max(self) -> None:
        e = ExtractedEntity(
            type=EntityType.URL,
            value="https://example.com",
            confidence=1.0,
            context="visit site",
        )
        assert e.confidence == 1.0

    def test_confidence_above_1_fails(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedEntity(
                type=EntityType.PERSON,
                value="John",
                confidence=1.1,
                context="email John",
            )

    def test_confidence_below_0_fails(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedEntity(
                type=EntityType.PERSON,
                value="John",
                confidence=-0.1,
                context="email John",
            )

    def test_empty_value_fails(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedEntity(
                type=EntityType.FILE_PATH,
                value="",
                confidence=0.5,
                context="file",
            )

    def test_empty_context_fails(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedEntity(
                type=EntityType.FILE_PATH,
                value="/path",
                confidence=0.5,
                context="",
            )

    def test_all_entity_types(self) -> None:
        for et in EntityType:
            e = ExtractedEntity(
                type=et,
                value="test",
                confidence=0.5,
                context="context",
            )
            assert e.type == et


# ---------------------------------------------------------------------------
# LayaClassification tests
# ---------------------------------------------------------------------------


class TestLayaClassification:
    def _make_laya(
        self,
        request_id: str = "req-001",
        category: LayaCategory = LayaCategory.ACTIONABLE,
        confidence: float = 0.9,
        ambiguous: bool = False,
        ambiguity_reason: str | None = None,
        **kwargs: Any,
    ) -> LayaClassification:
        defaults: dict[str, Any] = {
            "request_id": request_id,
            "category": category,
            "confidence": confidence,
            "ambiguous": ambiguous,
            "ambiguity_reason": ambiguity_reason,
        }
        defaults.update(kwargs)
        return LayaClassification(**defaults)

    def test_valid_minimal(self) -> None:
        lc = self._make_laya()
        assert lc.request_id == "req-001"
        assert lc.category == LayaCategory.ACTIONABLE
        assert lc.confidence == 0.9
        assert lc.ambiguous is False
        assert lc.ambiguity_reason is None
        assert lc.entities == []
        assert lc.characteristics == []

    def test_with_entities(self) -> None:
        entity = ExtractedEntity(
            type=EntityType.FILE_PATH,
            value="/tmp/test.txt",
            confidence=0.9,
            context="open file",
        )
        lc = self._make_laya(entities=[entity])
        assert len(lc.entities) == 1
        assert lc.entities[0].type == EntityType.FILE_PATH

    def test_with_characteristics(self) -> None:
        lc = self._make_laya(
            characteristics=[RequestCharacteristic.MULTI_STEP]
        )
        assert RequestCharacteristic.MULTI_STEP in lc.characteristics

    def test_all_categories(self) -> None:
        for cat in LayaCategory:
            lc = self._make_laya(category=cat)
            assert lc.category == cat

    def test_all_characteristics(self) -> None:
        for char in RequestCharacteristic:
            lc = self._make_laya(
                characteristics=[char]
            )
            assert char in lc.characteristics

    def test_ambiguous_with_reason(self) -> None:
        lc = self._make_laya(ambiguous=True, ambiguity_reason="unclear target")
        assert lc.ambiguous is True
        assert lc.ambiguity_reason == "unclear target"

    def test_ambiguous_without_reason_fails(self) -> None:
        with pytest.raises(ValidationError):
            self._make_laya(ambiguous=True, ambiguity_reason=None)

    def test_low_confidence_with_entities_and_no_ambiguity_passes(self) -> None:
        """Low confidence with entities and no ambiguity flag is allowed.

        ADR 04 does not prohibit this. The Intent Manager or downstream
        components may use low confidence as a signal without requiring
        an ambiguity flag.
        """
        entity = ExtractedEntity(
            type=EntityType.APP_NAME,
            value="browser",
            confidence=0.2,
            context="open",
        )
        lc = LayaClassification(
            request_id="req-1",
            category=LayaCategory.ACTIONABLE,
            entities=[entity],
            confidence=0.2,
            ambiguous=False,
            ambiguity_reason=None,
        )
        assert lc.confidence == 0.2

    def test_low_confidence_with_ambiguity_passes(self) -> None:
        """Low confidence is fine if the request is flagged as ambiguous."""
        entity = ExtractedEntity(
            type=EntityType.APP_NAME,
            value="browser",
            confidence=0.2,
            context="open",
        )
        lc = LayaClassification(
            request_id="req-1",
            category=LayaCategory.ACTIONABLE,
            entities=[entity],
            confidence=0.2,
            ambiguous=True,
            ambiguity_reason="low confidence extraction",
        )
        assert lc.confidence == 0.2

    def test_low_confidence_no_entities_passes(self) -> None:
        """Low confidence without entities is fine — no entities to be wrong."""
        lc = LayaClassification(
            request_id="req-1",
            category=LayaCategory.ACTIONABLE,
            confidence=0.2,
            ambiguous=False,
            ambiguity_reason=None,
        )
        assert lc.confidence == 0.2

    def test_serialize_roundtrip(self) -> None:
        lc = self._make_laya(
            category=LayaCategory.QUERY,
            confidence=0.85,
            ambiguous=True,
            ambiguity_reason="vague reference",
        )
        data = lc.model_dump(mode="json")
        lc2 = LayaClassification.model_validate(data)
        assert lc2.category == LayaCategory.QUERY
        assert lc2.confidence == 0.85
        assert lc2.ambiguous is True


# ---------------------------------------------------------------------------
# Intent tests
# ---------------------------------------------------------------------------


class TestIntent:
    def _make_intent(
        self,
        request_id: str = "req-001",
        laya_category: LayaCategory = LayaCategory.ACTIONABLE,
        confidence: float = 0.9,
        ambiguous: bool = False,
        **kwargs: Any,
    ) -> Intent:
        defaults: dict[str, Any] = {
            "request_id": request_id,
            "laya_category": laya_category,
            "normalized_form": "open file",
            "confidence": confidence,
            "ambiguous": ambiguous,
        }
        defaults.update(kwargs)
        return Intent(**defaults)

    def test_valid_minimal(self) -> None:
        intent = self._make_intent()
        assert intent.request_id == "req-001"
        assert intent.laya_category == LayaCategory.ACTIONABLE
        assert intent.normalized_form == "open file"
        assert intent.confidence == 0.9
        assert intent.ambiguous is False
        assert intent.entities == []
        assert intent.constraints == []

    def test_with_entities(self) -> None:
        entity = ExtractedEntity(
            type=EntityType.FILE_PATH,
            value="/tmp/test.txt",
            confidence=0.9,
            context="open",
        )
        intent = self._make_intent(entities=[entity])
        assert len(intent.entities) == 1
        assert intent.entities[0].type == EntityType.FILE_PATH

    def test_with_constraints(self) -> None:
        intent = self._make_intent(constraints=["read-only"])
        assert "read-only" in intent.constraints

    def test_all_laya_categories(self) -> None:
        for cat in LayaCategory:
            intent = self._make_intent(laya_category=cat)
            assert intent.laya_category == cat

    def test_confidence_bounds(self) -> None:
        intent_min = self._make_intent(confidence=0.0)
        assert intent_min.confidence == 0.0
        intent_max = self._make_intent(confidence=1.0)
        assert intent_max.confidence == 1.0

    def test_confidence_above_1_fails(self) -> None:
        with pytest.raises(ValidationError):
            self._make_intent(confidence=1.1)

    def test_confidence_below_0_fails(self) -> None:
        with pytest.raises(ValidationError):
            self._make_intent(confidence=-0.1)

    def test_empty_request_id_fails(self) -> None:
        with pytest.raises(ValidationError):
            self._make_intent(request_id="")

    def test_serialize_roundtrip(self) -> None:
        intent = self._make_intent(
            normalized_form="search web",
            confidence=0.8,
            ambiguous=True,
        )
        data = intent.model_dump(mode="json")
        intent2 = Intent.model_validate(data)
        assert intent2.normalized_form == "search web"
        assert intent2.confidence == 0.8
        assert intent2.ambiguous is True


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------


class TestInputToIntentPipeline:
    """Simulate the pipeline: Request -> LayaClassification -> Intent."""

    def test_full_pipeline_serialization(self) -> None:
        # Step 1: Input Processor produces a Request
        request = make_request(
            request_id="req-pipeline-1",
            raw_input="Open the config file at /etc/app/config.yaml",
            normalized_input="open the config file at /etc/app/config.yaml",
        )

        # Step 2: Laya classifies
        laya = LayaClassification(
            request_id=request.id,
            category=LayaCategory.ACTIONABLE,
            entities=[
                ExtractedEntity(
                    type=EntityType.FILE_PATH,
                    value="/etc/app/config.yaml",
                    confidence=0.95,
                    context="at /etc/app/config.yaml",
                )
            ],
            characteristics=[RequestCharacteristic.MULTI_STEP],
            confidence=0.92,
            ambiguous=False,
            ambiguity_reason=None,
        )

        # Step 3: Intent Manager normalizes
        intent = Intent(
            request_id=request.id,
            laya_category=laya.category,
            normalized_form="open configuration file",
            entities=laya.entities,
            constraints=["read-only"],
            confidence=0.9,
            ambiguous=False,
        )

        # Verify linkage
        assert intent.request_id == request.id
        assert intent.laya_category == laya.category
        assert len(intent.entities) == 1
        assert intent.entities[0].value == "/etc/app/config.yaml"

    def test_serialize_and_deserialize_pipeline(self) -> None:
        request = make_request(request_id="req-json-1")
        laya = LayaClassification(
            request_id=request.id,
            category=LayaCategory.QUERY,
            confidence=0.85,
            ambiguous=False,
            ambiguity_reason=None,
        )
        intent = Intent(
            request_id=request.id,
            laya_category=laya.category,
            normalized_form="what is the weather",
            confidence=0.85,
            ambiguous=False,
        )

        # Serialize each
        request_data = request.model_dump(mode="json")
        laya_data = laya.model_dump(mode="json")
        intent_data = intent.model_dump(mode="json")

        # Deserialize and verify
        r2 = Request.model_validate(request_data)
        l2 = LayaClassification.model_validate(laya_data)
        i2 = Intent.model_validate(intent_data)

        assert r2.id == request.id
        assert l2.category == LayaCategory.QUERY
        assert i2.normalized_form == "what is the weather"
