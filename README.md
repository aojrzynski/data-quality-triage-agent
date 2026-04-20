# Data Quality Triage Agent

A local Python agent that reads a dataset, checks for data quality issues, and produces structured findings plus a readable report.

## Planned scope
- CSV input first
- Local CLI run
- JSON findings output
- Markdown report output
- Optional LLM summary later

## Project status
Initial repo setup complete.

## Planned checks
- Missing values
- Duplicate keys
- Bad categorical values
- Date gaps
- Numeric outliers
- Basic schema surprises

## Run
For now, just test the placeholder CLI:

```bash
python -m src.cli
```