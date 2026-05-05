# Architecture Walkthrough

This is a module-level guide for readers learning the codebase.

- `src/io.py`
  - File loaders and artifact writers.
  - Keeps persistence concerns isolated.

- `src/intake.py`
  - Intake and tabular suitability logic.
  - Handles XLSX candidate ranking and dataset selection.

- `src/role_inference.py`
  - Deterministic role inference.
  - Produces assumptions for agent orchestration.

- `src/bindings.py`
  - Resolves role bindings with precedence and provenance.
  - Critical for deterministic, inspectable tool targeting.
  - Prevents hidden behavior changes by making override/inference/fallback decisions explicit.

- `src/planner.py`
  - Rule-based plan generation.
  - Uses resolved bindings (not raw inference) so overrides matter.

- `src/tools.py`
  - Thin tool abstraction over deterministic checks.
  - Lets agent mode execute checks dynamically without rewriting check logic.
  - Keeps orchestration separate from detection so checks remain straightforward to test.

- `src/checks.py`
  - Core deterministic data quality checks.

- `src/agent_runner.py`
  - Main agent loop.
  - Runs intake, inference, optional confirmation, planning, execution, investigations, and output writes.

- `src/investigation_tools.py`
  - Deterministic follow-up investigations for selected finding families.

- `src/triage_reporting.py`
  - Deterministic triage summary and agent report builders.

- `src/llm_summary.py`
  - Optional OpenAI-based report polish helpers.
  - Never authoritative for issue detection.
  - Failures in this layer should not block deterministic artifacts.

- `src/cli.py`
  - Entry point and mode boundary (`deterministic` vs `agent`).

## Why these boundaries matter

- Separating deterministic checks from orchestration keeps the detection layer stable while the agent layer evolves.
- Resolved bindings make tool targeting auditable and reproducible.
- Trace artifacts make debugging concrete: you can inspect planned actions, executed tools, skipped actions, and stop rationale.
