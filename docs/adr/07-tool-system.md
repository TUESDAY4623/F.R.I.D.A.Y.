# Tool System

## Overview

The Tool System provides the interface through which the Agent Orchestrator executes actions. In the current milestone, all tools are represented by **interfaces and deterministic mocks**. No real tool implementations exist.

## Tool Manager Interface

The Tool Manager is the single entry point for all tool execution. No component may invoke a tool directly — all tool access goes through the Tool Manager.

```
IToolManager
├── register(tool: ITool): void              // Register a tool
├── discover(): ToolDescriptor[]             // List available tools
├── execute(tool_name: string, params: object, context: ExecutionContext): ToolResult
├── validate_params(tool_name: string, params: object): ValidationResult         // (see ADR 04)  // (see ADR 04)
└── shutdown(): void
```

### ToolDescriptor

```
ToolDescriptor
├── name: string              // Unique tool identifier
├── description: string       // Human-readable description
├── parameters: Schema        // Expected parameter schema (ADR 04 schema reference)
├── category: string          // Tool category (e.g., "browser", "filesystem")
├── requires_approval: boolean // Whether policy approval is needed
└── mock: boolean             // Whether this is a mock implementation
```

### ToolResult

```
ToolResult
├── success: boolean           // Whether the execution succeeded
├── data: object               // Result data (if successful)
├── error: ErrorRecord          // Error details (if failed) — (see ADR 04)
├── duration_ms: number        // Execution duration
└── metadata: object           // Additional result metadata
```

### ExecutionContext

```
ExecutionContext
├── agent_state: AgentState    // Current agent state (read-only reference) — (see ADR 04)
├── task_graph_node_id: string // The node being executed
├── step_number: number        // Current step number
└── parameters: object         // Runtime parameters
```

## Tool Interface

All tools implement the `ITool` interface:

```
ITool
├── name: string                    // Unique identifier
├── description: string             // What the tool does
├── execute(context: ExecutionContext, params: object): Promise<ToolResult>
├── validate_params(params: object): ValidationResult
├── requires_approval: boolean      // Whether Policy Engine approval is needed
└── mock: boolean                   // Whether this is a mock implementation
```

## Downstream Tool Categories (Mocked)

The following tool categories are defined as interfaces. In the current milestone, each has a deterministic mock implementation.

### Policy Engine

```
IPolicyEngine
├── validate(action: ProposedAction, context: ExecutionContext): PolicyResult    // (see ADR 04)
├── approve(action: ProposedAction): ApprovalToken                                // (see ADR 04)
├── deny(action: ProposedAction, reason: string): DenialRecord                    // (see ADR 04)
└── rules: PolicyRule[]            // Active policy rules
```

### Browser Tools

```
IBrowserTool (implements ITool)
├── navigate(url: string): ToolResult
├── click(selector: string): ToolResult
├── type(selector: string, text: string): ToolResult
├── screenshot(): ToolResult
├── read_page(): ToolResult
└── close(): ToolResult
```

### Windows Tools

```
IWindowsTool (implements ITool)
├── open_application(app_name: string): ToolResult
├── send_keys(keys: string): ToolResult
├── read_window(title: string): ToolResult
├── screenshot(): ToolResult
└── clipboard_get(): ToolResult
```

### File System Tools

```
IFileSystemTool (implements ITool)
├── read_file(path: string): ToolResult
├── write_file(path: string, content: string): ToolResult
├── list_directory(path: string): ToolResult
├── delete_file(path: string): ToolResult
├── file_exists(path: string): ToolResult
└── get_file_info(path: string): ToolResult
```

### Vision

```
IVisionTool (implements ITool)
├── describe_image(image_data: object): ToolResult
├── read_text_from_image(image_data: object): ToolResult
├── compare_images(image_a: object, image_b: object): ToolResult
└── detect_objects(image_data: object): ToolResult
```

## Mock Tool Behavior

Mock tools must satisfy the following requirements:

1. **Deterministic:** Given the same inputs, a mock tool always returns the same output.
2. **Configurable:** Mock behavior can be configured per test scenario.
3. **Observable:** Mock invocations are recorded for test assertions.
4. **Failure simulation:** Mocks can be configured to simulate failures for testing error recovery paths.
5. **No side effects:** Mock tools do not modify real system state.

## Tool Registration

Tools are registered with the Tool Manager during system initialization:

1. The system creates tool instances (real or mock).
2. Each tool is registered with the Tool Manager via `register()`.
3. The Orchestrator discovers available tools via `discover()`.
4. The Orchestrator invokes tools via `execute()`.

In the current milestone, all tools are mocks registered at startup.

## Tool Execution Flow

When the Orchestrator executes a tool:

1. The Orchestrator identifies the tool name from the Task Graph node.
2. The Orchestrator calls `ToolManager.execute()` with the tool name, parameters, and execution context.
3. The Tool Manager looks up the tool, validates parameters, and invokes `tool.execute()`.
4. If the tool requires approval, the Tool Manager submits the action to the Policy Engine first.
5. The tool returns a `ToolResult`.
6. The Tool Manager returns the result to the Orchestrator.
7. The Orchestrator adds the result as an observation and proceeds to VERIFY.

## Security Constraints

1. All tool parameters must be validated before execution.
2. Tools that modify system state (write, delete, navigate) require Policy Engine approval.
3. Tools that only read data do not require approval.
4. The Policy Engine may deny any action regardless of tool type.
5. Denied actions are recorded and handled by the Error Recovery process.
