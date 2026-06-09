# Data Quality Triage Agent

Data Quality Triage Agent is a local, CLI-first Python project for inspecting tabular datasets (CSV/XLSX), detecting data quality issues with deterministic checks, and producing inspectable triage artifacts. It includes both a stable deterministic mode and a bounded agent mode that orchestrates deterministic tools without making LLM output authoritative.

> [!NOTE]
> **Part of the Data Agent Suite.**
> 
> This repo is one of 10 local-first data/AI agents built around practical data workflows, deterministic evidence, bounded LLM use, and review-ready artifacts.
> 
> The full ordered list of agents is included near the bottom of this README.
> 
> See the full suite overview: [Data Agent Suite](https://aojrzynski.github.io/agents/)

## Why this exists

I built this project to understand agents by building one from the inside out.

A simple way to check a spreadsheet is to upload it to ChatGPT and ask, “what looks wrong?” That can work for one-off analysis. But it hides the design questions I wanted to understand:

- what normal code should do instead of the LLM
- what the agent actually decides
- how to keep results repeatable
- how to manage token usage
- how to make the run inspectable after it finishes

This project explores those questions with a deliberately bounded data quality agent. The deterministic checks do the issue detection. The agent layer decides which checks to run, which columns to use, when to investigate, and how to record the process. The LLM layer is optional and only polishes the final report.

## Why not just ask an LLM?

For a personal one-off task, asking an LLM to inspect a file may be enough.

This project is about a different pattern: use deterministic code for the parts that should be repeatable, testable, and cheap, then use agent logic to orchestrate that code.

That matters when you want:

- consistent checks across many files
- lower and more predictable token usage
- less data sent to an external model
- clearer evidence for every finding
- a trace of what the agent planned, ran, skipped, and investigated

The point is not that an LLM cannot inspect data. The point is that not every part of the workflow should be an LLM call.

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

## How this can be extended

The project is split into layers so future work can focus on one area without rewriting everything:

- add more deterministic checks
- change the agent planning/investigation behaviour
- expand the optional LLM layer

See `docs/extension_paths.md` for more detail.

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

## Further reading

- `PROJECT_SCOPE.md` — what is in and out of scope
- `ARCHITECTURE.md` — short architecture overview
- `PLANS.md` — roadmap and future work
- `docs/how_it_works.md` — runtime flow walkthrough
- `docs/architecture_walkthrough.md` — module-by-module guide
- `docs/adding_a_new_check.md` — how to extend the deterministic check layer
- `docs/extension_paths.md` — ways to extend the project

---

> [!NOTE]
> **Data Agent Suite**  
> This repo is part of the **Data Agent Suite**: 10 local-first data/AI agents focused on practical data workflows, deterministic evidence, bounded LLM use, and review-ready artifacts.
> 
> See the full suite overview: [Data Agent Suite](https://aojrzynski.github.io/agents/)
>
> 1. **Data Quality Triage Agent**
> 2. [Data Reconciliation Agent](https://github.com/aojrzynski/data-reconciliation-agent)
> 3. [Data Dictionary Agent](https://github.com/aojrzynski/data-dictionary-agent)
> 4. [Data Contract Review Agent](https://github.com/aojrzynski/data-contract-review-agent)
> 5. [Sensitive Field Review Agent](https://github.com/aojrzynski/sensitive-field-review-agent)
> 6. [Data Test Suggestion Agent](https://github.com/aojrzynski/data-test-suggestion-agent)
> 7. [Dataset Onboarding Reviewer Workflow](https://github.com/aojrzynski/dataset-onboarding-reviewer-workflow)
> 8. [Data Quality Investigation Workflow](https://github.com/aojrzynski/data-quality-investigation-workflow)
> 9. [Project Evidence Review Agent](https://github.com/aojrzynski/project-evidence-review-agent)
> 10. [Data Migration Readiness Review Agent](https://github.com/aojrzynski/data-migration-readiness-review-agent)
