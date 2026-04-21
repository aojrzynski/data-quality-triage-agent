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

## Planned checks
- Missing values
- Duplicate keys
- Bad categorical values
- Date gaps
- Numeric outliers
- Basic schema surprises

## Run

```bash
python -m src.cli --input sample_data/clean/orders_clean.csv
```

## Outputs
The agent writes files into `outputs/`:
- `*_profile.json`
- `*_report.md`