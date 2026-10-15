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


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def write_schema(model, filename: str) -> Path:
    """Generate and write JSON schema for a Pydantic model."""
    schema = model.model_json_schema()
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

    # Enums as simple string schemas
    enum_dir = SCHEMA_DIR
    for name, enum_cls in [
        ("entity-type", EntityType),
        ("request-characteristic", RequestCharacteristic),
        ("laya-category", LayaCategory),
        ("task-type", TaskType),
        ("complexity", Complexity),
        ("node-status", NodeStatus),
        ("edge-type", EdgeType),
    ]:
        enum_schema = {
            "type": "string",
            "enum": [v.value for v in enum_cls],
            "description": enum_cls.__doc__ or f"Enum: {enum_cls.__name__}",
        }
        out_path = enum_dir / f"{name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(enum_schema, f, indent=2)
        generated.append((name, out_path))

    print(f"Generated {len(generated)} schemas in {SCHEMA_DIR}")
    for name, path in generated:
        print(f"  {name}: {path}")


if __name__ == "__main__":
    generate_all()
