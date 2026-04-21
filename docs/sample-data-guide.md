# Sample Data Guide

This project includes small synthetic datasets for development, testing, and demo purposes.

## Why these files exist
- They make the repo runnable out of the box
- They let us test known issues
- They are safe to publish publicly

## Datasets

### `sample_data/clean/orders_clean.csv`
A clean baseline orders dataset with no intentional issues.

### `sample_data/broken/orders_nulls.csv`
Contains missing values in `customer_id`.

### `sample_data/broken/orders_duplicate_keys.csv`
Contains duplicate values in `order_id`.

### `sample_data/broken/orders_bad_categories.csv`
Contains typo / unexpected values in `status`.

### `sample_data/broken/orders_date_gaps.csv`
Contains gaps in the `order_date` sequence.

### `sample_data/broken/orders_outliers.csv`
Contains a clear numeric outlier in `amount`.

### `sample_data/broken/orders_schema_surprises.csv`
Contains a schema mismatch:
- missing expected column: `region`
- unexpected extra column: `sales_channel`

## Expected result files
Expected findings are stored in:

`tests/fixtures/expected/`

These files are used for automated validation tests.