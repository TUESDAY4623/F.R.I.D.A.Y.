# Jarvis — Project Instructions

## Project

Jarvis is an agentic desktop AI system designed to understand natural-language requests, plan tasks, reason over current state, and execute actions through controlled tools.

The system is being developed as an agentic core first, followed by integration with real desktop, browser, filesystem, and application tools.

---

# Current Development Boundary

The current implementation target is:

User Input
→ Input Processor
→ Intent Manager
→ Laya
→ Task Profiler
→ Planner
→ Agent State
→ Decision Engine
→ Agent Orchestrator

The current development milestone ends at the Agent Orchestrator.

Downstream systems such as Policy Engine, Tool Manager, Browser Tools, Windows Tools, File System Tools, Vision, and real-world execution should initially be represented using interfaces and deterministic mocks.

Do not implement real downstream automation unless explicitly requested.

---

# Core Architecture Principles

1. Laya classifies user requests.
2. Intent Manager owns intent understanding and normalization.
3. Task Profiler determines task characteristics and requirements.
4. Planner proposes an initial execution strategy.
5. Task Graph represents the initial strategy.
6. Task Graph is revisable and must not be treated as a rigid workflow.
7. Agent State represents the current runtime state of a task.
8. Decision Engine determines what should happen next.
9. Agent Orchestrator controls the agentic execution loop.
10. LLMs propose structured decisions; they do not directly execute tools.
11. All LLM outputs must be schema validated.
12. Real tool execution must occur behind explicit interfaces.
13. Agent State is different from persistent memory.
14. The Orchestrator must react to observations rather than blindly following the original plan.
15. The system must support retry, replan, ask-user, completion, and failure paths.
16. Architecture changes must be documented.

---

# Agentic Control Loop

The fundamental loop is:

OBSERVE
→ DECIDE
→ ACT
→ OBSERVE RESULT
→ VERIFY
→ UPDATE STATE
→ DECIDE AGAIN

Possible decisions:

- EXECUTE
- OBSERVE
- REPLAN
- RETRY
- ASK_USER
- WAIT
- COMPLETE
- FAIL

---

# Current Development Strategy

Development must happen incrementally.

Phase 0:
Project specification and repository foundation.

Phase 1:
Core contracts and schemas.

Phase 2:
Input Processor and Intent Layer.

Phase 3:
Task Profiler and Planner.

Phase 4:
Agent State.

Phase 5:
Decision Engine and Reasoning Provider.

Phase 6:
Agent Orchestrator.

Phase 7:
Deterministic mock tools and end-to-end agent tests.

Phase 8:
Real tool integrations.

Do not skip phases without explicit approval.

---

# Engineering Rules

## Before implementing a component

1. Read the relevant architecture documentation.
2. Read the component specification.
3. Read the relevant data contracts.
4. Identify dependencies.
5. Create an implementation plan.
6. Implement only the requested scope.

## After implementation

1. Add unit tests.
2. Add contract tests where applicable.
3. Run the relevant test suite.
4. Check architecture compliance.
5. Check type correctness.
6. Check error handling.
7. Report what was changed.

---

# Coding Principles

- Prefer clear and maintainable code over clever abstractions.
- Keep components independently testable.
- Use explicit interfaces between major components.
- Avoid hidden global state.
- Avoid unnecessary dependencies.
- Keep provider-specific code behind adapters.
- Use dependency injection where appropriate.
- Prefer typed contracts.
- Validate external and LLM-generated data.
- Never silently swallow errors.
- Do not duplicate business logic across components.

---

# LLM Rules

LLMs must not directly control arbitrary application behavior.

The flow should be:

LLM
→ Structured Output
→ Schema Validation
→ Decision Validation
→ Agent Orchestrator
→ Action Interface

Never:

LLM
→ arbitrary text
→ execute

---

# Testing Requirements

Every major component must have tests.

Required test categories:

- Unit tests
- Contract/schema tests
- Integration tests
- Agent-loop tests
- Failure/recovery tests

The agentic core must be testable without real external applications.

---

# Scope Control

Do not prematurely implement:

- Voice wake word
- GUI
- Windows automation
- Browser automation
- Vision
- Persistent memory
- Vector database
- Multi-agent architecture
- Complex RAG
- Blender/Figma integrations
- Background autonomous operation

These belong to later phases.

---

# Source of Truth

The following hierarchy should be respected:

1. CLAUDE.md
2. docs/
3. schemas/
4. source code
5. tests

If code conflicts with the documented architecture, do not silently redefine the architecture through code.

Raise the conflict and propose a documented change.

---

# Current Phase

CURRENT_PHASE = 0

Current objective:

Establish the project specification, architecture documentation, repository structure, contracts, development rules, and testing strategy before implementing the agentic core.

Do not begin Phase 1 implementation until Phase 0 is explicitly completed.