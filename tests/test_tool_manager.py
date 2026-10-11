import time

from jarvis.tools.contract import BaseTool, ToolContract, ToolResult
from jarvis.tools.manager import ToolManager
from jarvis.tools.registry import ToolRegistry
from jarvis.types import PolicyDecision, RiskLevel


class EchoTool(BaseTool):
    @property
    def contract(self):
        return ToolContract(
            name="echo",
            description="Returns the supplied message",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
            },
            output_schema={"type": "object"},
            risk_level=RiskLevel.LOW,
            reversible=True,
            rollback_strategy=None,
            timeout=5.0,
            idempotency=True,
            required_capabilities=[],
            platform_support=["windows"],
        )

    def execute(self, params):
        return ToolResult(
            success=True,
            data={"message": params["message"]},
        )


class FailingTool(EchoTool):
    @property
    def contract(self):
        contract = super().contract
        return contract.model_copy(update={"name": "failing"})

    def execute(self, params):
        raise RuntimeError("test failure")


class SlowTool(EchoTool):
    @property
    def contract(self):
        return super().contract.model_copy(
            update={"name": "slow", "timeout": 0.1}
        )

    def execute(self, params):
        time.sleep(1)
        return ToolResult(success=True, data={"message": "finished"})


class DenyPolicy:
    def check(self, action_name, arguments, contract=None):
        return PolicyDecision.DENY


class ConfirmPolicy:
    def check(self, action_name, arguments, contract=None):
        return PolicyDecision.CONFIRM


class RawResultTool(EchoTool):
    @property
    def contract(self):
        return super().contract.model_copy(update={"name": "raw_result"})

    def execute(self, params):
        return {"message": params["message"]}


def make_manager(tool, policy_engine=None):
    registry = ToolRegistry()
    registry.register(tool)
    return ToolManager(
        registry=registry,
        policy_engine=policy_engine,
    )


def test_successful_dispatch():
    manager = make_manager(EchoTool())

    result = manager.dispatch("echo", {"message": "hello"})

    assert result.success is True
    assert result.data == {"message": "hello"}


def test_unknown_tool():
    manager = ToolManager(registry=ToolRegistry())

    result = manager.dispatch("does_not_exist", {})

    assert result.success is False
    assert "not found" in result.error.lower()


def test_missing_required_argument():
    manager = make_manager(EchoTool())

    result = manager.dispatch("echo", {})

    assert result.success is False
    assert result.error is not None


def test_wrong_argument_type():
    manager = make_manager(EchoTool())

    result = manager.dispatch("echo", {"message": 123})

    assert result.success is False
    assert result.error is not None


def test_policy_deny():
    manager = make_manager(EchoTool(), DenyPolicy())

    result = manager.dispatch("echo", {"message": "blocked"})

    assert result.success is False
    assert "den" in result.error.lower()


def test_policy_confirm():
    manager = make_manager(EchoTool(), ConfirmPolicy())

    result = manager.dispatch("echo", {"message": "approval needed"})

    assert result.success is False
    assert "confirm" in result.error.lower() or "approval" in result.error.lower()


def test_execution_exception():
    manager = make_manager(FailingTool())

    result = manager.dispatch("failing", {"message": "test"})

    assert result.success is False
    assert "test failure" in result.error


def test_timeout():
    manager = make_manager(SlowTool())

    result = manager.dispatch("slow", {"message": "wait"})

    assert result.success is False
    assert "timed out" in result.error.lower()


def test_raw_result_is_normalized():
    manager = make_manager(RawResultTool())

    result = manager.dispatch("raw_result", {"message": "hello"})

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.data == {"message": "hello"}
