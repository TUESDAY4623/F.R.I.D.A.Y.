"""Tests for Group B contracts: Task Understanding layer."""

import json
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError

from jarvis.contracts.models.group_a import (
    Intent,
    LayaCategory,
    LayaClassification,
    Request,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_request(
    request_id: str = "req-001",
    raw_input: str = "Open the file",
    normalized_input: str = "open the file",
) -> Request:
    return Request(
        id=request_id,
        raw_input=raw_input,
        normalized_input=normalized_input,
    )


def make_intent(request_id: str = "req-001") -> Intent:
    return Intent(
        request_id=request_id,
        laya_category=LayaCategory.ACTIONABLE,
        normalized_form="open file",
        confidence=0.9,
        ambiguous=False,
    )


def make_task_profile(
    intent_id: str = "intent-001",
    task_type: TaskType = TaskType.MULTI_STEP,
    complexity: Complexity = Complexity.MEDIUM,
    estimated_steps: int = 3,
) -> TaskProfile:
    return TaskProfile(
        intent_id=intent_id,
        task_type=task_type,
        requirements=["browser", "filesystem"],
        constraints=["read-only"],
        complexity=complexity,
        estimated_steps=estimated_steps,
        prerequisites=["browser_ready"],
    )


def make_node(
    node_id: str = "node-1",
    node_type: str = "tool_call",
    description: str = "Do something",
    expected_outcome: str = "Task completed",
    status: NodeStatus = NodeStatus.PENDING,
    retry_limit: int = 3,
    parameters: dict[str, Any] | None = None,
) -> TaskGraphNode:
    return TaskGraphNode(
        id=node_id,
        type=node_type,
        description=description,
        expected_outcome=expected_outcome,
        status=status,
        retry_limit=retry_limit,
        parameters=parameters or {},
    )


# ---------------------------------------------------------------------------
# TaskProfile tests
# ---------------------------------------------------------------------------


class TestTaskProfile:
    def test_valid_minimal(self) -> None:
        profile = make_task_profile()
        assert profile.intent_id == "intent-001"
        assert profile.task_type == TaskType.MULTI_STEP
        assert profile.complexity == Complexity.MEDIUM
        assert profile.estimated_steps == 3
        assert profile.requirements == ["browser", "filesystem"]
        assert profile.constraints == ["read-only"]
        assert profile.prerequisites == ["browser_ready"]
        assert profile.metadata == {}

    def test_empty_lists_default(self) -> None:
        profile = TaskProfile(
            intent_id="int-1",
            task_type=TaskType.SINGLE_STEP,
            complexity=Complexity.LOW,
            estimated_steps=1,
        )
        assert profile.requirements == []
        assert profile.constraints == []
        assert profile.prerequisites == []
        assert profile.metadata == {}

    def test_all_task_types(self) -> None:
        for tt in TaskType:
            profile = make_task_profile(task_type=tt)
            assert profile.task_type == tt

    def test_all_complexities(self) -> None:
        for c in Complexity:
            profile = make_task_profile(complexity=c)
            assert profile.complexity == c

    def test_with_metadata(self) -> None:
        profile = make_task_profile()
        assert profile.metadata == {}
        profile.metadata["profiler_version"] = "0.1"
        assert profile.metadata["profiler_version"] == "0.1"

    def test_empty_intent_id_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_task_profile(intent_id="")

    def test_estimated_steps_zero_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_task_profile(estimated_steps=0)

    def test_estimated_steps_negative_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_task_profile(estimated_steps=-1)

    def test_estimated_steps_one_passes(self) -> None:
        profile = make_task_profile(estimated_steps=1)
        assert profile.estimated_steps == 1

    def test_serialize_roundtrip(self) -> None:
        profile = make_task_profile(
            intent_id="int-abc",
            task_type=TaskType.EXPLORATORY,
            complexity=Complexity.HIGH,
            estimated_steps=5,
        )
        data = profile.model_dump(mode="json")
        profile2 = TaskProfile.model_validate(data)
        assert profile2.intent_id == "int-abc"
        assert profile2.task_type == TaskType.EXPLORATORY
        assert profile2.complexity == Complexity.HIGH
        assert profile2.estimated_steps == 5

    def test_links_to_intent(self) -> None:
        """TaskProfile.intent_id should match an Intent.request_id."""
        intent = make_intent(request_id="intent-42")
        profile = make_task_profile(intent_id=intent.request_id)
        assert profile.intent_id == intent.request_id


# ---------------------------------------------------------------------------
# TaskGraphNode tests
# ---------------------------------------------------------------------------


class TestTaskGraphNode:
    def test_valid_minimal(self) -> None:
        node = make_node()
        assert node.id == "node-1"
        assert node.type == "tool_call"
        assert node.description == "Do something"
        assert node.expected_outcome == "Task completed"
        assert node.status == NodeStatus.PENDING
        assert node.retry_limit == 3
        assert node.parameters == {}
        assert node.result == {}

    def test_with_parameters(self) -> None:
        node = make_node(
            parameters={"path": "/tmp/file.txt", "mode": "r"},
        )
        assert node.parameters["path"] == "/tmp/file.txt"

    def test_with_result(self) -> None:
        node = make_node()
        node.result = {"success": True, "output": "done"}
        assert node.result["success"] is True

    def test_all_node_statuses(self) -> None:
        for status in NodeStatus:
            node = make_node(status=status)
            assert node.status == status

    def test_retry_limit_default(self) -> None:
        node = make_node(retry_limit=3)
        assert node.retry_limit == 3

    def test_retry_limit_zero(self) -> None:
        node = make_node(retry_limit=0)
        assert node.retry_limit == 0

    def test_retry_limit_negative_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_node(retry_limit=-1)

    def test_empty_id_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_node(node_id="")

    def test_empty_type_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_node(node_type="")

    def test_empty_description_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_node(description="")

    def test_empty_expected_outcome_fails(self) -> None:
        with pytest.raises(ValidationError):
            make_node(expected_outcome="")

    def test_serialize_roundtrip(self) -> None:
        node = make_node(
            node_id="node-abc",
            node_type="ask_user",
            description="Confirm action",
            status=NodeStatus.ACTIVE,
            retry_limit=5,
            parameters={"question": "Proceed?"},
        )
        data = node.model_dump(mode="json")
        node2 = TaskGraphNode.model_validate(data)
        assert node2.id == "node-abc"
        assert node2.type == "ask_user"
        assert node2.retry_limit == 5
        assert node2.status == NodeStatus.ACTIVE
        assert node2.parameters["question"] == "Proceed?"


# ---------------------------------------------------------------------------
# TaskGraphEdge tests
# ---------------------------------------------------------------------------


class TestTaskGraphEdge:
    def test_valid_sequence(self) -> None:
        edge = TaskGraphEdge(from_="a", to="b", type=EdgeType.SEQUENCE)
        assert edge.from_ == "a"
        assert edge.to == "b"
        assert edge.type == EdgeType.SEQUENCE

    def test_valid_condition(self) -> None:
        edge = TaskGraphEdge(from_="a", to="b", type=EdgeType.CONDITION)
        assert edge.type == EdgeType.CONDITION

    def test_valid_alternative(self) -> None:
        edge = TaskGraphEdge(from_="a", to="b", type=EdgeType.ALTERNATIVE)
        assert edge.type == EdgeType.ALTERNATIVE

    def test_alias_from_works(self) -> None:
        """The 'from' key in a dict should map to from_ via alias."""
        data = {"from": "src", "to": "dst", "type": "sequence"}
        edge = TaskGraphEdge.model_validate(data)
        assert edge.from_ == "src"

    def test_from_underscore_input_still_accepted(self) -> None:
        """populate_by_name keeps the Python name 'from_' accepted on input."""
        data = {"from_": "src", "to": "dst", "type": "sequence"}
        edge = TaskGraphEdge.model_validate(data)
        assert edge.from_ == "src"

    def test_all_edge_types(self) -> None:
        for et in EdgeType:
            edge = TaskGraphEdge(from_="x", to="y", type=et)
            assert edge.type == et

    def test_empty_from_fails(self) -> None:
        with pytest.raises(ValidationError):
            TaskGraphEdge(from_="", to="b", type=EdgeType.SEQUENCE)

    def test_empty_to_fails(self) -> None:
        with pytest.raises(ValidationError):
            TaskGraphEdge(from_="a", to="", type=EdgeType.SEQUENCE)

    def test_invalid_type_fails(self) -> None:
        with pytest.raises(ValidationError):
            TaskGraphEdge(from_="a", to="b", type="invalid")

    def test_serialize_roundtrip(self) -> None:
        edge = TaskGraphEdge(from_="n1", to="n2", type=EdgeType.CONDITION)
        data = edge.model_dump(mode="json")
        edge2 = TaskGraphEdge.model_validate(data)
        assert edge2.from_ == "n1"
        assert edge2.to == "n2"
        assert edge2.type == EdgeType.CONDITION


# ---------------------------------------------------------------------------
# TaskGraph tests
# ---------------------------------------------------------------------------


class TestTaskGraph:
    def test_valid_minimal(self) -> None:
        n1 = make_node(node_id="n1")
        graph = TaskGraph(
            id="graph-1",
            nodes=[n1],
            edges=[],
            entry_node_id="n1",
        )
        assert graph.id == "graph-1"
        assert len(graph.nodes) == 1
        assert graph.nodes[0].id == "n1"
        assert graph.edges == []
        assert graph.entry_node_id == "n1"
        assert graph.metadata == {}

    def test_with_metadata(self) -> None:
        graph = TaskGraph(
            id="graph-1",
            nodes=[make_node(node_id="n1")],
            edges=[],
            entry_node_id="n1",
        )
        graph.metadata = {"planner_version": "0.1"}
        assert graph.metadata["planner_version"] == "0.1"

    def test_edge_references_valid_node(self) -> None:
        """Edges must reference node IDs that exist in the graph."""
        graph = TaskGraph(
            id="graph-1",
            nodes=[make_node(node_id="n1"), make_node(node_id="n2")],
            edges=[TaskGraphEdge(from_="n1", to="n2", type=EdgeType.SEQUENCE)],
            entry_node_id="n1",
        )
        assert len(graph.edges) == 1
        assert graph.edges[0].from_ == "n1"

    def test_edge_references_nonexistent_source_fails(self) -> None:
        with pytest.raises(ValidationError, match="does not exist"):
            TaskGraph(
                id="graph-1",
                nodes=[make_node(node_id="n1")],
                edges=[TaskGraphEdge(from_="nonexistent", to="n1", type=EdgeType.SEQUENCE)],
                entry_node_id="n1",
            )

    def test_edge_references_nonexistent_target_fails(self) -> None:
        with pytest.raises(ValidationError, match="does not exist"):
            TaskGraph(
                id="graph-1",
                nodes=[make_node(node_id="n1")],
                edges=[TaskGraphEdge(from_="n1", to="nonexistent", type=EdgeType.SEQUENCE)],
                entry_node_id="n1",
            )

    def test_entry_node_not_in_graph_fails(self) -> None:
        with pytest.raises(ValidationError, match="does not match any node"):
            TaskGraph(
                id="graph-1",
                nodes=[make_node(node_id="n1")],
                edges=[],
                entry_node_id="nonexistent",
            )

    def test_duplicate_node_ids_fails(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate node ID"):
            TaskGraph(
                id="graph-1",
                nodes=[
                    make_node(node_id="n1"),
                    make_node(node_id="n1"),
                ],
                edges=[],
                entry_node_id="n1",
            )

    def test_empty_node_list_with_entry_fails(self) -> None:
        """entry_node_id cannot reference a node if there are no nodes."""
        with pytest.raises(ValidationError, match="does not match any node"):
            TaskGraph(
                id="graph-1",
                nodes=[],
                edges=[],
                entry_node_id="n1",
            )

    def test_three_node_linear_chain(self) -> None:
        """Build a simple 3-node linear task graph."""
        n1 = make_node(node_id="fetch", node_type="tool_call", description="Fetch data")
        n2 = make_node(node_id="process", node_type="tool_call", description="Process data")
        n3 = make_node(node_id="respond", node_type="tool_call", description="Respond")

        graph = TaskGraph(
            id="graph-linear",
            nodes=[n1, n2, n3],
            edges=[
                TaskGraphEdge(from_="fetch", to="process", type=EdgeType.SEQUENCE),
                TaskGraphEdge(from_="process", to="respond", type=EdgeType.SEQUENCE),
            ],
            entry_node_id="fetch",
        )
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2
        assert graph.entry_node_id == "fetch"

    def test_branching_with_condition_edge(self) -> None:
        """Graph with a conditional branch."""
        n1 = make_node(node_id="check", node_type="observe", description="Check condition")
        n2 = make_node(node_id="branch-a", node_type="tool_call", description="Branch A")
        n3 = make_node(node_id="branch-b", node_type="tool_call", description="Branch B")

        graph = TaskGraph(
            id="graph-branch",
            nodes=[n1, n2, n3],
            edges=[
                TaskGraphEdge(from_="check", to="branch-a", type=EdgeType.CONDITION),
                TaskGraphEdge(from_="check", to="branch-b", type=EdgeType.ALTERNATIVE),
            ],
            entry_node_id="check",
        )
        assert graph.edges[0].type == EdgeType.CONDITION
        assert graph.edges[1].type == EdgeType.ALTERNATIVE

    def test_serialize_roundtrip(self) -> None:
        nodes = [
            make_node(node_id="n1", node_type="tool_call", description="Step 1"),
            make_node(node_id="n2", node_type="observe", description="Step 2"),
        ]
        edges = [TaskGraphEdge(from_="n1", to="n2", type=EdgeType.SEQUENCE)]
        graph = TaskGraph(
            id="graph-rt",
            nodes=nodes,
            edges=edges,
            entry_node_id="n1",
        )
        data = graph.model_dump(mode="json")
        graph2 = TaskGraph.model_validate(data)
        assert graph2.id == "graph-rt"
        assert len(graph2.nodes) == 2
        assert graph2.entry_node_id == "n1"
        assert graph2.edges[0].from_ == "n1"
        assert graph2.edges[0].to == "n2"


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------


class TestTaskUnderstandingPipeline:
    """Simulate the pipeline: Intent -> TaskProfile -> TaskGraph."""

    def test_intent_to_task_profile_linkage(self) -> None:
        intent = make_intent(request_id="req-1")
        profile = make_task_profile(intent_id=intent.request_id)
        assert profile.intent_id == intent.request_id

    def test_task_profile_to_task_graph_linkage(self) -> None:
        profile = make_task_profile(complexity=Complexity.HIGH, estimated_steps=5)
        n1 = make_node(
            node_id="step-1",
            node_type="tool_call",
            description=f"Step 1 of {profile.estimated_steps}-step task",
        )
        graph = TaskGraph(
            id="graph-1",
            nodes=[n1],
            edges=[],
            entry_node_id="step-1",
        )
        assert graph.nodes[0].id == "step-1"
        assert graph.entry_node_id == "step-1"

    def test_full_pipeline_serialization(self) -> None:
        """Request -> Intent -> TaskProfile -> TaskGraph serialize round-trip."""
        request = make_request(request_id="req-full")
        intent = make_intent(request_id=request.id)
        profile = make_task_profile(
            intent_id=intent.request_id,
            task_type=TaskType.MULTI_STEP,
            complexity=Complexity.MEDIUM,
        )
        n1 = make_node(node_id="n1", node_type="tool_call", description="Read file")
        n2 = make_node(node_id="n2", node_type="tool_call", description="Process data")
        graph = TaskGraph(
            id="graph-full",
            nodes=[n1, n2],
            edges=[TaskGraphEdge(from_="n1", to="n2", type=EdgeType.SEQUENCE)],
            entry_node_id="n1",
        )

        # Serialize all
        request_data = request.model_dump(mode="json")
        intent_data = intent.model_dump(mode="json")
        profile_data = profile.model_dump(mode="json")
        graph_data = graph.model_dump(mode="json")

        # Deserialize all
        r2 = Request.model_validate(request_data)
        i2 = Intent.model_validate(intent_data)
        p2 = TaskProfile.model_validate(profile_data)
        g2 = TaskGraph.model_validate(graph_data)

        assert r2.id == request.id
        assert i2.request_id == intent.request_id
        assert p2.intent_id == intent.request_id
        assert len(g2.nodes) == 2
        assert g2.entry_node_id == "n1"


# ---------------------------------------------------------------------------
# Schema alignment tests
# ---------------------------------------------------------------------------


class TestSchemaAlignment:
    """Verify generated JSON schemas match Pydantic model definitions."""

    @staticmethod
    def _load(name: str) -> dict:
        from pathlib import Path

        schema_dir = Path(__file__).resolve().parent.parent.parent / "schemas"
        with open(schema_dir / name, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_task_profile_required_fields(self) -> None:
        schema = self._load("task-profile.json")
        assert set(schema["required"]) == {
            "intent_id",
            "task_type",
            "complexity",
            "estimated_steps",
        }

    def test_task_profile_optional_fields(self) -> None:
        schema = self._load("task-profile.json")
        assert "requirements" not in schema["required"]
        assert "constraints" not in schema["required"]
        assert "prerequisites" not in schema["required"]
        assert "metadata" not in schema["required"]

    def test_task_profile_estimated_steps_minimum(self) -> None:
        schema = self._load("task-profile.json")
        assert schema["properties"]["estimated_steps"]["exclusiveMinimum"] == 0

    def test_task_profile_complexity_enum(self) -> None:
        schema = self._load("task-profile.json")
        assert schema["$defs"]["Complexity"]["enum"] == ["low", "medium", "high"]

    def test_task_profile_task_type_enum(self) -> None:
        schema = self._load("task-profile.json")
        assert schema["$defs"]["TaskType"]["enum"] == [
            "single-step",
            "multi-step",
            "exploratory",
        ]

    def test_task_graph_node_required_fields(self) -> None:
        schema = self._load("task-graph-node.json")
        assert set(schema["required"]) == {
            "id",
            "type",
            "description",
            "expected_outcome",
        }

    def test_task_graph_node_optional_fields(self) -> None:
        schema = self._load("task-graph-node.json")
        assert "parameters" not in schema["required"]
        assert "retry_limit" not in schema["required"]
        assert "status" not in schema["required"]
        assert "result" not in schema["required"]

    def test_task_graph_node_retry_limit_default(self) -> None:
        schema = self._load("task-graph-node.json")
        assert schema["properties"]["retry_limit"]["default"] == 3

    def test_task_graph_node_status_enum(self) -> None:
        schema = self._load("task-graph-node.json")
        assert schema["$defs"]["NodeStatus"]["enum"] == [
            "pending",
            "active",
            "completed",
            "failed",
            "skipped",
            "retrying",
        ]

    def test_task_graph_edge_required_fields(self) -> None:
        schema = self._load("task-graph-edge.json")
        assert set(schema["required"]) == {"from", "to", "type"}

    def test_task_graph_edge_type_enum(self) -> None:
        schema = self._load("task-graph-edge.json")
        assert schema["$defs"]["EdgeType"]["enum"] == [
            "sequence",
            "condition",
            "alternative",
        ]

    def test_task_graph_required_fields(self) -> None:
        schema = self._load("task-graph.json")
        # nodes and edges have default_factory=list, so they are optional
        assert set(schema["required"]) == {"id", "entry_node_id"}

    def test_task_graph_optional_fields(self) -> None:
        schema = self._load("task-graph.json")
        assert "metadata" not in schema["required"]

    def test_no_extra_properties(self) -> None:
        """All Group B schemas should forbid additional properties."""
        for name in [
            "task-profile.json",
            "task-graph-node.json",
            "task-graph-edge.json",
            "task-graph.json",
        ]:
            schema = self._load(name)
            assert schema.get("additionalProperties") is False, (
                f"{name} should forbid additional properties"
            )

    def test_model_dump_matches_schemas(self) -> None:
        """Pydantic model_dump output should validate against generated schemas."""
        profile = make_task_profile()
        jsonschema.validate(
            profile.model_dump(mode="json"), self._load("task-profile.json")
        )

        node = make_node()
        jsonschema.validate(
            node.model_dump(mode="json"), self._load("task-graph-node.json")
        )

        edge = TaskGraphEdge(from_="a", to="b", type=EdgeType.SEQUENCE)
        jsonschema.validate(
            edge.model_dump(mode="json"),
            self._load("task-graph-edge.json"),
        )

        # A graph WITH edges exercises the nested edge serialization path.
        graph = TaskGraph(
            id="g",
            nodes=[make_node(node_id="a"), make_node(node_id="b")],
            edges=[TaskGraphEdge(from_="a", to="b", type=EdgeType.SEQUENCE)],
            entry_node_id="a",
        )
        jsonschema.validate(
            graph.model_dump(mode="json"), self._load("task-graph.json")
        )

    def test_schema_files_exist(self) -> None:
        """All expected schema files should be present."""
        from pathlib import Path

        schema_dir = Path(__file__).resolve().parent.parent.parent / "schemas"
        expected = [
            "task-profile.json",
            "task-graph-node.json",
            "task-graph-edge.json",
            "task-graph.json",
            "task-type.json",
            "complexity.json",
            "node-status.json",
            "edge-type.json",
        ]
        for name in expected:
            assert (schema_dir / name).exists(), f"Missing schema: {name}"


# ---------------------------------------------------------------------------
# TaskGraphEdge from/by_alias regression tests
# ---------------------------------------------------------------------------
# These tests verify the fix for IMPORTANT I-1: TaskGraphEdge default
# serialization must emit the documented field name "from", not "from_".
# ---------------------------------------------------------------------------


class TestTaskGraphEdgeFromSerialization:
    """Regression tests for TaskGraphEdge.from_ field serialization.

    The Python attribute is named `from_` (because `from` is a reserved
    keyword). The documented external contract uses `from`. With
    serialize_by_alias=True, model_dump() must emit `from` by default so
    the output conforms to the JSON schema without any by_alias flag.
    """

    def test_model_dump_emits_from_not_from_(self) -> None:
        edge = TaskGraphEdge(from_="n1", to="n2", type=EdgeType.SEQUENCE)
        data = edge.model_dump()
        assert "from" in data, "model_dump() must emit 'from', not 'from_'"
        assert "from_" not in data, "model_dump() must not emit 'from_'"

    def test_model_dump_mode_json_emits_from_not_from_(self) -> None:
        edge = TaskGraphEdge(from_="n1", to="n2", type=EdgeType.SEQUENCE)
        data = edge.model_dump(mode="json")
        assert "from" in data, "model_dump(mode='json') must emit 'from', not 'from_'"
        assert "from_" not in data, "model_dump(mode='json') must not emit 'from_'"

    def test_model_dump_json_string_emits_from_not_from_(self) -> None:
        edge = TaskGraphEdge(from_="n1", to="n2", type=EdgeType.SEQUENCE)
        json_str = edge.model_dump_json()
        assert '"from"' in json_str, "model_dump_json() must emit 'from', not 'from_'"
        assert '"from_"' not in json_str, "model_dump_json() must not emit 'from_'"

    def test_serialized_result_validates_against_schema(self) -> None:
        edge = TaskGraphEdge(from_="src", to="dst", type=EdgeType.CONDITION)
        data = edge.model_dump(mode="json")
        jsonschema.validate(data, self._load("task-graph-edge.json"))

    def test_serialized_result_roundtrips(self) -> None:
        edge = TaskGraphEdge(from_="a", to="b", type=EdgeType.ALTERNATIVE)
        data = edge.model_dump(mode="json")
        restored = TaskGraphEdge.model_validate(data)
        assert restored.from_ == edge.from_
        assert restored.to == edge.to
        assert restored.type == edge.type

    def test_nested_in_taskgraph_model_dump_emits_from(self) -> None:
        n1 = make_node(node_id="step-1")
        n2 = make_node(node_id="step-2")
        edge = TaskGraphEdge(from_="step-1", to="step-2", type=EdgeType.SEQUENCE)
        graph = TaskGraph(
            id="graph-serial",
            nodes=[n1, n2],
            edges=[edge],
            entry_node_id="step-1",
        )
        data = graph.model_dump(mode="json")
        assert "from" in data["edges"][0]
        assert "from_" not in data["edges"][0]

    def test_nested_in_taskgraph_validates_against_schema(self) -> None:
        n1 = make_node(node_id="x")
        n2 = make_node(node_id="y")
        edge = TaskGraphEdge(from_="x", to="y", type=EdgeType.SEQUENCE)
        graph = TaskGraph(
            id="graph-schema",
            nodes=[n1, n2],
            edges=[edge],
            entry_node_id="x",
        )
        data = graph.model_dump(mode="json")
        jsonschema.validate(data, self._load("task-graph.json"))

    @staticmethod
    def _load(name: str) -> dict:
        from pathlib import Path

        schema_dir = Path(__file__).resolve().parent.parent.parent / "schemas"
        with open(schema_dir / name, "r", encoding="utf-8") as f:
            return json.load(f)

