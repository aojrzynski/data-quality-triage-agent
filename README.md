# Data Quality Triage Agent

A local Python CLI project for data quality triage.

## What it is today
The current implementation is a **deterministic data quality triage tool** with an explicit intake stage (tabular suitability + sheet selection) and optional LLM-written summary support.

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

Agent mode boundary exists but is not implemented yet:

```bash
python -m src.cli --input sample_data/clean/orders_clean.csv --mode agent
```

## Outputs
The CLI writes files into `outputs/`:
- `*_profile.json`
- `*_report.md`

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
