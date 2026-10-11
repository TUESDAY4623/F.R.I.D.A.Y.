"""Tests for Group A JSON schema validation."""

import json
from pathlib import Path

import jsonschema
import pytest

from jarvis.contracts.models.group_a import (
    EntityType,
    ExtractedEntity,
    Intent,
    LayaCategory,
    LayaClassification,
    Request,
    RequestCharacteristic,
)


SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"


def load_schema(name: str) -> dict:
    """Load a generated JSON schema file."""
    path = SCHEMA_DIR / name
    assert path.exists(), f"Schema file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestSchemaFilesExist:
    """Verify all expected schema files were generated."""

    def test_request_schema_exists(self) -> None:
        assert (SCHEMA_DIR / "request.json").exists()

    def test_extracted_entity_schema_exists(self) -> None:
        assert (SCHEMA_DIR / "extracted-entity.json").exists()

    def test_laya_classification_schema_exists(self) -> None:
        assert (SCHEMA_DIR / "laya-classification.json").exists()

    def test_intent_schema_exists(self) -> None:
        assert (SCHEMA_DIR / "intent.json").exists()

    def test_entity_type_schema_exists(self) -> None:
        assert (SCHEMA_DIR / "entity-type.json").exists()

    def test_request_characteristic_schema_exists(self) -> None:
        assert (SCHEMA_DIR / "request-characteristic.json").exists()

    def test_laya_category_schema_exists(self) -> None:
        assert (SCHEMA_DIR / "laya-category.json").exists()


class TestSchemaValidation:
    """Verify that valid data passes JSON Schema validation and invalid data fails."""

    def test_request_schema_validates_correct_data(self) -> None:
        schema = load_schema("request.json")
        data = {
            "id": "req-001",
            "raw_input": "Open the file",
            "normalized_input": "open the file",
            "timestamp": "2025-01-01T00:00:00Z",
            "metadata": {},
        }
        jsonschema.validate(data, schema)

    def test_request_schema_rejects_missing_id(self) -> None:
        schema = load_schema("request.json")
        data = {
            "raw_input": "Open the file",
            "normalized_input": "open the file",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_request_schema_rejects_empty_raw_input(self) -> None:
        schema = load_schema("request.json")
        data = {
            "id": "req-001",
            "raw_input": "",
            "normalized_input": "open the file",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_request_schema_rejects_extra_properties(self) -> None:
        schema = load_schema("request.json")
        data = {
            "id": "req-001",
            "raw_input": "test",
            "normalized_input": "test",
            "unknown_field": "value",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_extracted_entity_schema_validates_correct_data(self) -> None:
        schema = load_schema("extracted-entity.json")
        data = {
            "type": "file_path",
            "value": "/home/user/file.txt",
            "confidence": 0.95,
            "context": "opening file",
        }
        jsonschema.validate(data, schema)

    def test_extracted_entity_schema_rejects_invalid_confidence(self) -> None:
        schema = load_schema("extracted-entity.json")
        data = {
            "type": "file_path",
            "value": "/path",
            "confidence": 1.5,
            "context": "context",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_extracted_entity_schema_rejects_unknown_type(self) -> None:
        schema = load_schema("extracted-entity.json")
        data = {
            "type": "unknown_type",
            "value": "test",
            "confidence": 0.5,
            "context": "context",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_laya_classification_schema_validates_correct_data(self) -> None:
        schema = load_schema("laya-classification.json")
        data = {
            "request_id": "req-001",
            "category": "actionable",
            "confidence": 0.9,
            "ambiguous": False,
            "ambiguity_reason": None,
        }
        jsonschema.validate(data, schema)

    def test_laya_classification_schema_rejects_unknown_category(self) -> None:
        schema = load_schema("laya-classification.json")
        data = {
            "request_id": "req-001",
            "category": "nonexistent",
            "confidence": 0.9,
            "ambiguous": False,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_intent_schema_validates_correct_data(self) -> None:
        schema = load_schema("intent.json")
        data = {
            "request_id": "req-001",
            "laya_category": "actionable",
            "normalized_form": "open file",
            "confidence": 0.9,
            "ambiguous": False,
        }
        jsonschema.validate(data, schema)

    def test_intent_schema_rejects_invalid_laya_category(self) -> None:
        schema = load_schema("intent.json")
        data = {
            "request_id": "req-001",
            "laya_category": "invalid",
            "normalized_form": "open file",
            "confidence": 0.9,
            "ambiguous": False,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_entity_type_enum_values(self) -> None:
        schema = load_schema("entity-type.json")
        assert schema["type"] == "string"
        assert "file_path" in schema["enum"]
        assert "app_name" in schema["enum"]
        assert "url" in schema["enum"]
        assert len(schema["enum"]) == 12

    def test_request_characteristic_enum_values(self) -> None:
        schema = load_schema("request-characteristic.json")
        assert schema["type"] == "string"
        assert "multi-step" in schema["enum"]
        assert "requires-confirmation" in schema["enum"]
        assert len(schema["enum"]) == 7

    def test_laya_category_enum_values(self) -> None:
        schema = load_schema("laya-category.json")
        assert schema["type"] == "string"
        assert "informational" in schema["enum"]
        assert "actionable" in schema["enum"]
        assert "query" in schema["enum"]
        assert "command" in schema["enum"]
        assert len(schema["enum"]) == 4


class TestSchemaMatchesPydanticModel:
    """Verify that generated schemas accurately reflect Pydantic model definitions."""

    def test_request_schema_required_fields(self) -> None:
        schema = load_schema("request.json")
        assert set(schema["required"]) == {"id", "raw_input", "normalized_input"}

    def test_request_schema_optional_fields_not_required(self) -> None:
        schema = load_schema("request.json")
        assert "timestamp" not in schema["required"]
        assert "metadata" not in schema["required"]

    def test_extracted_entity_all_fields_required(self) -> None:
        schema = load_schema("extracted-entity.json")
        assert set(schema["required"]) == {"type", "value", "confidence", "context"}

    def test_extracted_entity_confidence_bounds(self) -> None:
        schema = load_schema("extracted-entity.json")
        confidence_schema = schema["properties"]["confidence"]
        assert confidence_schema["minimum"] == 0.0
        assert confidence_schema["maximum"] == 1.0
        assert confidence_schema["type"] == "number"

    def test_laya_classification_required_fields(self) -> None:
        schema = load_schema("laya-classification.json")
        assert set(schema["required"]) == {
            "request_id",
            "category",
            "confidence",
            "ambiguous",
        }

    def test_laya_classification_optional_fields(self) -> None:
        schema = load_schema("laya-classification.json")
        assert "entities" not in schema["required"]
        assert "characteristics" not in schema["required"]
        assert "ambiguity_reason" not in schema["required"]

    def test_intent_required_fields(self) -> None:
        schema = load_schema("intent.json")
        assert set(schema["required"]) == {
            "request_id",
            "laya_category",
            "normalized_form",
            "confidence",
            "ambiguous",
        }

    def test_intent_optional_fields(self) -> None:
        schema = load_schema("intent.json")
        assert "entities" not in schema["required"]
        assert "constraints" not in schema["required"]

    def test_schemas_have_no_extra_properties(self) -> None:
        """All core schemas should forbid extra properties."""
        for name in [
            "request.json",
            "extracted-entity.json",
            "laya-classification.json",
            "intent.json",
        ]:
            schema = load_schema(name)
            assert schema.get("additionalProperties") is False, (
                f"{name} should forbid additional properties"
            )

    def test_datetime_fields_have_format(self) -> None:
        """Datetime fields should use the date-time format."""
        request_schema = load_schema("request.json")
        assert request_schema["properties"]["timestamp"]["format"] == "date-time"

    def test_model_dump_matches_schema(self) -> None:
        """Pydantic model_dump output should validate against the generated schema."""
        model = LayaClassification(
            request_id="req-1",
            category=LayaCategory.ACTIONABLE,
            confidence=0.9,
            ambiguous=False,
        )
        data = model.model_dump(mode="json")
        schema = load_schema("laya-classification.json")
        jsonschema.validate(data, schema)
