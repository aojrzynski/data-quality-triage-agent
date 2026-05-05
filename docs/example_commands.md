# Example Commands

## Deterministic mode (clean CSV)

```bash
python -m src.cli --input sample_data/clean/orders_clean.csv --mode deterministic
```

## Deterministic mode (broken CSV)

```bash
python -m src.cli --input sample_data/broken/orders_nulls.csv --mode deterministic
```

## Agent mode

```bash
python -m src.cli --input sample_data/broken/orders_outliers.csv --mode agent
```

## Agent mode with interactive assumption confirmation

```bash
python -m src.cli --input sample_data/broken/orders_duplicate_keys.csv --mode agent --confirm-assumptions
```

## Agent mode with override flags

```bash
python -m src.cli \
  --input sample_data/broken/orders_bad_categories.csv \
  --mode agent \
  --agent-key-columns order_id \
  --agent-date-columns order_date \
  --agent-numeric-columns amount \
  --agent-categorical-columns region
```

## Agent mode with LLM polish

```bash
python -m src.cli --input sample_data/broken/orders_schema_surprises.csv --mode agent --llm-summary
```

## XLSX with explicit sheet

```bash
python -m src.cli --input sample_data/clean/orders_clean.xlsx --sheet Sheet1 --mode deterministic
```

## Run tests

```bash
python -m pytest
```
