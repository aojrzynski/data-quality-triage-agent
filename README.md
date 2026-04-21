# Data Quality Triage Agent

A local Python agent that reads a dataset, checks for data quality issues, and produces structured findings plus a readable report.

## Planned scope
- CSV input first
- Local CLI run
- JSON findings output
- Markdown report output
- Optional LLM summary later

## Current status
Current version can:
- load a CSV file
- build a structured dataset profile
- run first-pass data quality checks
- score findings by severity
- write JSON output
- write a Markdown report

Implemented checks:
- missing values
- duplicate keys
- unexpected categorical values

## Planned scope
- CSV and XLSX input
- Local CLI run
- JSON findings output
- Markdown report output
- Optional LLM summary later

## Run

```bash
python -m src.cli --input sample_data/clean/orders_clean.csv
python -m src.cli --input sample_data/clean/orders_clean.xlsx
```

## Outputs
The agent writes files into `outputs/`:
- `*_profile.json`
- `*_report.md`

## Optional LLM summary
You can optionally generate an LLM-written summary on top of the deterministic findings.

This uses the OpenAI API and requires `OPENAI_API_KEY` to be set.

Example:

```bash
python -m src.cli \
  --input sample_data/broken/orders_bad_categories.xlsx \
  --config config/default_config.json \
  --expected tests/fixtures/expected/orders_bad_categories_expected.json \
  --llm-summary
```