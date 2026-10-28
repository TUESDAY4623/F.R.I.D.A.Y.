# TESTING — Organization, Commands, Results, and Limitations

Last verified: commit `c5db884`; local run **431 passed, 0 failed** in
13.19 s (`python -m pytest tests -q`, Python 3.14.0, 2026-10-28).

## 1. Test suite organization

All tests live in `tests/contracts/` (Phase 1 contract foundation):

| File | Scope | pytest count |
|---|---|---|
| `test_group_a.py` | Group A units/pipeline (Request, LayaClassification, Intent, entities, enums) | 36 |
| `test_group_a_schemas.py` | Group A model↔JSON-schema alignment | 32 |
| `test_group_b.py` | TaskProfile, TaskGraph(+Node/Edge), enums (parameterized) | 70 |
| `test_group_c.py` | AgentState, ExecutionStep, all 8 decision variants + union, RuntimeConfig (parameterized) | 166 |
| `test_group_d.py` | ProposedAction, ToolResult, PolicyResult, ValidationResult | 72 |
| `test_group_e.py` | UserResponse, WaitCondition | 55 |
| **Total** | | **431** |

Test configuration: `pyproject.toml` — `testpaths = ["tests"]`,
`pythonpath = ["src"]`, dev dependency `pytest>=8.0`.

## 2. Commands

```bash
# Full suite
python -m pytest tests -q          # 431 passed (local, verified)

# One group
python -m pytest tests/contracts/test_group_c.py -q

# Regenerate JSON schemas and confirm no drift (working tree stays clean)
python scripts/generate_schemas.py # prints "Generated 48 schemas"
git status --porcelain            # expect no schemas/ changes
```

Dependencies: `pydantic>=2.0`, `jsonschema>=4.0` (runtime); `pytest` (dev).
No lockfile (`uv.lock` is gitignored and absent in the current tree).

## 3. What the suite covers

- **Unit tests** for every contract model's validation rules (non-empty
  strings, confidence bounds 0.0–1.0, enum constraints, relationship
  invariants).
- **Schema-alignment tests** confirming model ↔ JSON schema consistency.
- **Decision-union tests** covering the discriminated-union acceptance/rejection
  rules from ADR 04 (required params per decision type, e.g. `FAIL` requires
  `reason`).

## 4. Verification limitations — read before quoting results

- **No CI exists.** The GitHub Actions workflow (`.github/workflows/test.yml`)
  was deleted in commit `031c27a` ("Reset repository"). Therefore:
  - Never cite "CI passed" for the current tree — there is no CI.
  - All test evidence is **local** (command + count + Python version + date).
- **Test counts are point-in-time.** 431 is verified at `c5db884`; re-run
  before quoting.
- **Python version:** `pyproject.toml` requires `>=3.11`; the verified run
  used 3.14.0.
- The pre-reset tree's "87 tests / 100% pass" claims belong to the
  **historical** implementation (deleted in `031c27a`) and must not be mixed
  with current evidence — see [ARCHITECTURE_HISTORY.md](ARCHITECTURE_HISTORY.md).

## 5. Testing strategy reference

The broader testing requirements (unit, contract/schema, integration,
agent-loop, failure/recovery categories; core must be testable without real
external applications) are specified in `docs/adr/12-testing-strategy.md` and
`CLAUDE.md` §Testing Requirements. As of `c5db884` only the unit +
contract/schema categories exist (the contract suite above); integration,
agent-loop, and failure/recovery test categories land with Phases 2–7.
