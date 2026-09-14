# Build Progress Log

Tracks build progress date-wise per work session.
Rules: Append-only, new entries added at the top (most recent first). Never edit or delete past entries.
## 2026-09-14 — Phase 1 (Adarsh)

- what was built/changed: Implemented the Tool Manager execution gateway. It now validates tool requests and arguments, looks up registered tools, performs the Policy Engine check, handles DENY/CONFIRM decisions, executes tools with the contract timeout, catches execution failures, and normalizes tool results.

- what was tested and the result: Added Tool Manager tests covering successful dispatch, unknown tools, argument validation, policy decisions, execution errors, timeout handling, and result normalization. GitHub Actions test result: **23 passed, 0 failed**.

- what's still open or blocking the next person: Real filesystem tools and full risk-based Policy Engine enforcement remain separate Phase 1 work. UI/log viewer and remaining Phase 0 integration work are also outside this Tool Manager task.
## 2026-09-12 — Phase 0 (Adarsh)

- what was built/changed: Added two temporary contract-proof tools, `read_file` and `list_directory`, implementing the shared `BaseTool` interface and declaring complete `ToolContract` metadata. Both tools are read-only and declared LOW risk. Verified that the tools can be registered and retrieved through `ToolRegistry`. Phase 0 Policy Engine remains an empty pass-through that returns `PolicyDecision.ALLOW`; real risk-tier enforcement is deferred to Phase 1.

- what was tested and the result: Added tests covering tool contracts, tool execution, Registry registration/lookup, and Policy Engine ALLOW pass-through. Test execution result: **14 passed, 0 failed** via GitHub Actions.

- what's still open or blocking the next person: Real filesystem tool set and real risk-based Policy Engine enforcement remain deferred to Phase 1. Phase 0 step-ordering verification across all components and remaining UI/log viewer work remain open.


## 2026-09-12 — Phase 0 (Sujeet/Adarsh)
- what was built/changed: Initialized modular monolith repository structure (`src/jarvis/`); implemented Tool Registry contract per Section 11 (`ToolContract`, `ToolRegistry`, `BaseTool`, with safety validation rules for risk levels and reversibility); implemented Orchestrator 11-step canonical loop as an explicit state machine (`CanonicalLoopStateMachine`, `AgentOrchestrator`) with every step as a no-op stub logging its own name; implemented Event Logger as the first real component per Section 13 with sensitive credential redaction, in-memory query buffer, and live streaming subscription; added component stubs for all Section 4 subsystems; set up `main.py` Hello Loop runner and `uv` project configuration.
- what was tested and the result: Ran `main.py` Hello Loop (11/11 canonical steps logged in exact order, 16 streamed events captured, probe tool registered and executed); ran automated test suite via pytest with 10 passed, 0 failed across `test_tool_registry.py`, `test_event_logger.py`, and `test_orchestrator_loop.py`.
- what's still open or blocking the next person: Bare text I/O shell and live streaming log viewer pane (Tanmay) are still open; step-ordering test verification suite across all components is still open before Phase 0 exit sign-off.
