# Data Quality Triage Agent

Data Quality Triage Agent is a local, CLI-first Python project for inspecting tabular datasets (CSV/XLSX), detecting data quality issues with deterministic checks, and producing inspectable triage artifacts. It includes both a stable deterministic mode and a bounded agent mode that orchestrates deterministic tools without making LLM output authoritative.

## What this project demonstrates

- Deterministic data quality checking with reproducible results.
- Rule-based agent orchestration on top of deterministic tools.
- Explicit intake, role inference, assumption tracking, and binding resolution.
- Inspectable outputs (`json` trace + markdown report) designed for debugging and learning.
- Optional LLM-polished narrative that never replaces deterministic findings.

## Why this is an "agent"

The agent mode does more than run a fixed checklist. It:

- infers likely semantic column roles,
- resolves role bindings via explicit precedence (override -> confirmation -> inference -> config fallback),
- builds a rule-based execution plan,
- executes deterministic tools using resolved bindings,
- runs bounded second-pass investigations,
- records a full trace of what happened and why.

This is agentic orchestration, not autonomous open-ended reasoning.

## Quick start

```bash
python -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Windows (Git Bash):

```bash
source .venv/Scripts/activate
python -m pip install -e ".[dev]"
```

Run deterministic mode:

```bash
python -m src.cli --input sample_data/clean/orders_clean.csv --mode deterministic
```

Run agent mode:

```bash
python -m src.cli --input sample_data/broken/orders_nulls.csv --mode agent
```

## Example commands

```bash
# deterministic mode (CSV)
python -m src.cli --input sample_data/broken/orders_outliers.csv --mode deterministic

# deterministic mode (XLSX + explicit sheet)
python -m src.cli --input sample_data/broken/orders_date_gaps.xlsx --sheet Sheet1 --mode deterministic

# agent mode (rule-based planner/executor)
python -m src.cli --input sample_data/broken/orders_bad_categories.csv --mode agent

# agent mode with interactive assumption confirmation
python -m src.cli --input sample_data/broken/orders_duplicate_keys.csv --mode agent --confirm-assumptions

# agent mode with non-interactive overrides
python -m src.cli \
  --input sample_data/broken/orders_nulls.csv \
  --mode agent \
  --agent-key-columns order_id \
  --agent-date-columns order_date \
  --agent-numeric-columns amount \
  --agent-categorical-columns region

# optional LLM-polished report in agent mode
python -m src.cli --input sample_data/broken/orders_schema_surprises.csv --mode agent --llm-summary
```

More copy/paste commands: `docs/example_commands.md`.

## Deterministic mode vs agent mode

### Deterministic mode

- Config-driven deterministic checks.
- Stable baseline behavior.
- Outputs:
  - `*_profile.json`
  - `*_report.md`
  - optional `*_llm_summary.md` when `--llm-summary` is used.

### Agent mode

- Intake + role inference + assumption tracking.
- Rule-based planner and deterministic tool execution.
- Resolved role-to-tool bindings with explicit provenance.
- Bounded investigations for selected finding families.
- Outputs:
  - `*_agent_trace.json`
  - `*_agent_report.md`
  - optional `*_agent_report_llm.md` when `--llm-summary` is used.

## Input formats

- `.csv`
- `.xlsx`

For XLSX, if `--sheet` is omitted, intake ranks sheets and auto-selects the strongest tabular candidate.

## Output artifacts

All outputs are written to `outputs/` by default (`--output-dir` to change).

Agent traces are intentionally verbose so execution is inspectable and reproducible.

## Optional LLM polish

LLM usage is optional and used only for narrative polish.

- Required only when using `--llm-summary`:
  - `OPENAI_API_KEY`
  - optional `OPENAI_MODEL`
- Not required for deterministic mode or core agent mode.
- Deterministic findings, trace, and deterministic reports remain source of truth.

## Example use cases

- Triage a newly delivered CSV before downstream analysis.
- Compare how the same dataset behaves in deterministic mode vs agent mode.
- Demonstrate inspectable agent orchestration in a portfolio project.
- Use as a teaching codebase for bounded agent design.

## Project structure

- `src/cli.py` — CLI and mode boundary.
- `src/intake.py` — suitability checks + XLSX sheet selection.
- `src/role_inference.py` — deterministic role inference.
- `src/bindings.py` — resolved binding logic.
- `src/planner.py` — rule-based action planning.
- `src/tools.py` / `src/checks.py` — deterministic tool wrappers + check logic.
- `src/agent_runner.py` — agent loop and artifact generation.
- `src/investigation_tools.py` — bounded second-pass investigations.
- `src/triage_reporting.py` — deterministic triage summary/report.
- `src/llm_summary.py` — optional LLM-polish helpers.
- `docs/` — learning-oriented walkthroughs.

## Run tests

```bash
python -m pytest
```

## Limitations and non-goals

- Not a general spreadsheet intelligence system.
- Works best for tabular CSV/XLSX with a clear header row.
- No web UI.
- No database-backed architecture.
- No deep adaptive replanning or open-ended autonomy.
- LLM is not used to detect issues and is not authoritative.

## Roadmap / future ideas

See `PLANS.md` for focused future work, including:

- richer planning heuristics,
- stronger investigation playbooks,
- improved validation ergonomics,
- more test coverage for edge-case datasets.
