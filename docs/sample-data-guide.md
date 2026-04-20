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

Expected issue:
- missing values in `customer_id`

### `sample_data/broken/orders_duplicate_keys.csv`
Contains duplicate values in `order_id`.

Expected issue:
- duplicate key in `order_id`

### `sample_data/broken/orders_bad_categories.csv`
Contains typo / unexpected values in `status`.

Expected issue:
- unexpected categorical values in `status`

## Expected result files
Expected findings are stored in:

`tests/fixtures/expected/`

These files will be used later for automated tests.