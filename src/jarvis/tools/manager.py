"""Tool Manager for controlled tool execution."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import TYPE_CHECKING, Any, Dict, Optional

from jarvis.tools.contract import ToolResult
from jarvis.tools.registry import ToolRegistry, get_tool_registry
from jarvis.types import PolicyDecision

if TYPE_CHECKING:
    from jarvis.policy import PolicyEngine


class ToolManager:
    """Controlled execution gateway for registered tools."""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        policy_engine: Optional[PolicyEngine] = None,
    ) -> None:
        from jarvis.policy import get_policy_engine

        self.registry = registry or get_tool_registry()
        self.policy_engine = policy_engine or get_policy_engine()

    def dispatch(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        approval_decision: Optional[Any] = None,
    ) -> ToolResult:
        """Validate, authorize, execute, and normalize a tool request."""

        # 1. Validate request
        if not isinstance(tool_name, str) or not tool_name.strip():
            return ToolResult(
                success=False,
                error="Tool name must be a non-empty string",
            )

        if not isinstance(arguments, dict):
            return ToolResult(
                success=False,
                error="Tool arguments must be a dictionary",
            )

        # 2. Find registered tool
        if not self.registry.has(tool_name):
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found in registry",
            )

        tool = self.registry.get(tool_name)
        contract = tool.contract

        # 3. Validate arguments against the basic input schema
        validation_error = self._validate_arguments(
            arguments,
            contract.input_schema,
        )

        if validation_error:
            return ToolResult(
                success=False,
                error=validation_error,
            )

        # 4. Policy check
        decision = self.policy_engine.check(
            action_name=tool_name,
            arguments=arguments,
            contract=contract,
        )

        if decision == PolicyDecision.DENY:
            return ToolResult(
                success=False,
                error=f"Policy denied tool '{tool_name}'",
                metadata={"policy_decision": decision.value},
            )

        if decision == PolicyDecision.CONFIRM:
            from jarvis.types import ApprovalDecision

            is_approved = (
                approval_decision is True
                or approval_decision == ApprovalDecision.APPROVE
                or (isinstance(approval_decision, str) and approval_decision.lower() == "approve")
            )
            if not is_approved:
                return ToolResult(
                    success=False,
                    error=f"Tool '{tool_name}' requires approval before execution",
                    metadata={"policy_decision": decision.value},
                )

        # 5. Execute with timeout
        executor = ThreadPoolExecutor(max_workers=1)

        try:
            future = executor.submit(tool.execute, arguments)

            try:
                result = future.result(timeout=contract.timeout)
            except TimeoutError:
                future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)

                return ToolResult(
                    success=False,
                    error=(
                        f"Tool '{tool_name}' timed out after "
                        f"{contract.timeout} seconds"
                    ),
                    metadata={"policy_decision": decision.value},
                )

        except Exception as exc:
            executor.shutdown(wait=False, cancel_futures=True)

            return ToolResult(
                success=False,
                error=f"Execution failed: {exc}",
                metadata={"policy_decision": decision.value},
            )
        else:
            executor.shutdown(wait=True)

        # 6. Normalize result
        if isinstance(result, ToolResult):
            metadata = dict(result.metadata or {})
            metadata["policy_decision"] = decision.value

            return ToolResult(
                success=result.success,
                data=result.data,
                error=result.error,
                metadata=metadata,
            )

        return ToolResult(
            success=True,
            data=result,
            metadata={
                "policy_decision": decision.value,
                "normalized": True,
            },
        )

    @staticmethod
    def _validate_arguments(
        arguments: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> Optional[str]:
        """Perform basic validation of required fields and primitive types."""

        if not isinstance(schema, dict):
            return None

        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required:
            if field not in arguments:
                return f"Missing required argument: '{field}'"

        for field, value in arguments.items():
            if field not in properties:
                continue

            expected_type = properties[field].get("type")

            if expected_type == "string" and not isinstance(value, str):
                return f"Argument '{field}' must be a string"

            if expected_type == "object" and not isinstance(value, dict):
                return f"Argument '{field}' must be an object"

            if expected_type == "array" and not isinstance(value, list):
                return f"Argument '{field}' must be an array"

            if expected_type == "boolean" and not isinstance(value, bool):
                return f"Argument '{field}' must be a boolean"

            if expected_type == "integer" and (
                not isinstance(value, int) or isinstance(value, bool)
            ):
                return f"Argument '{field}' must be an integer"

            if expected_type == "number" and (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
            ):
                return f"Argument '{field}' must be a number"

        return None
