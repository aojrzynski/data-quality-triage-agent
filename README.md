# Data Quality Triage Agent

A local Python CLI project for data quality triage.

## What it is today
The current implementation is a **deterministic data quality triage tool** with an explicit intake stage (tabular suitability + sheet selection), deterministic role inference/assumption generation, and optional LLM-written summary support.

## Where it's going
The target is a genuine **Data Quality Triage Agent** with a separate agent mode layered on top of deterministic checks.

For canonical details, see:
- `PROJECT_SCOPE.md`
- `ARCHITECTURE.md`
- `PLANS.md`

## Run

```bash
python -m src.cli --input sample_data/clean/orders_clean.csv
python -m src.cli --input sample_data/clean/orders_clean.xlsx
python -m src.cli --input sample_data/clean/orders_clean.xlsx --sheet Sheet1
python -m src.cli --input sample_data/clean/orders_clean.csv --mode deterministic
```

Agent mode now runs a first deterministic, rule-based planner/executor:

```bash
python -m src.cli --input sample_data/clean/orders_clean.csv --mode agent
```

Agent mode plans which deterministic tools to execute, resolves role-to-tool column bindings (override -> inferred -> config fallback), runs tools against those resolved bindings, and writes an inspectable trace artifact.

## Outputs
The CLI writes files into `outputs/`:
- Deterministic mode: `*_profile.json`, `*_report.md`
- Agent mode: `*_agent_trace.json`

## Optional LLM summary
You can optionally generate an LLM-written summary on top of deterministic findings.

This uses the OpenAI API and requires `OPENAI_API_KEY`.

```bash
python -m src.cli \
  --input sample_data/broken/orders_bad_categories.xlsx \
  --config config/default_config.json \
  --expected tests/fixtures/expected/orders_bad_categories_expected.json \
  --llm-summary
```


## Intake behavior (Stage 4)
- Input runs through deterministic intake before checks.
- CSV inputs use a single candidate dataset.
- XLSX inputs auto-rank sheets when `--sheet` is omitted, then select the strongest tabular candidate.
- Intake reports suitability (`suitable|borderline|unsuitable`) with score and warnings in CLI output.
- Suitability is heuristic and intentionally limited (no OCR, no full spreadsheet semantics).


## Role inference behavior (Stage 5)
- Deterministic mode now performs rule-based column role inference after intake and before checks.
- Inferred assumptions include likely `key`, `date`, `numeric_measure`, and `categorical` columns.
- Each inferred assumption carries confidence + provenance and is marked as `inferred`.
- This output is currently informative only: deterministic checks are still driven by config.


## Agent mode behavior (Stage 7)
- Runs intake and role inference first.
- Builds a rule-based plan that always starts with schema/completeness checks, then conditionally adds role-driven tool families.
- Executes selected deterministic tools through the tool layer.
- Records planned/executed actions and explicit stop rationale.
- Produces a structured `*_agent_trace.json` execution trace.
- Still does **not** implement investigation tools, human confirmations, or full triage narrative output.

- Optional non-interactive agent overrides are available in agent mode only: `--agent-key-columns`, `--agent-date-columns`, `--agent-numeric-columns`, `--agent-categorical-columns`.
- Categorical validation in agent mode still requires configured rule sets per selected column; columns without rules are explicitly skipped and traced.
- Deterministic mode remains config-driven and rejects agent-only override flags.
