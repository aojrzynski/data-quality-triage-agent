import pandas as pd

from src.role_inference import infer_column_roles


def _columns(candidates: list) -> set[str]:
    return {candidate.column_name for candidate in candidates}


def test_orders_dataset_infers_sensible_roles() -> None:
    df = pd.read_csv("sample_data/clean/orders_clean.csv")
    result = infer_column_roles(df)

    assert "order_id" in _columns(result.key_candidates)
    assert "order_date" in _columns(result.date_candidates)
    assert "amount" in _columns(result.numeric_measure_candidates)
    assert {"status", "region"}.intersection(_columns(result.categorical_candidates))


def test_trades_fixture_infers_financialish_roles() -> None:
    df = pd.read_csv("tests/fixtures/role_inference/trades_sample.csv")
    result = infer_column_roles(df)

    assert "trade_id" in _columns(result.key_candidates)
    assert "trade_date" in _columns(result.date_candidates)
    assert "notional" in _columns(result.numeric_measure_candidates)
    assert "instrument_type" in _columns(result.categorical_candidates)


def test_inference_attaches_confidence_and_inferred_status() -> None:
    df = pd.read_csv("tests/fixtures/role_inference/trades_sample.csv")
    result = infer_column_roles(df)

    assert result.assumptions
    for assumption in result.assumptions:
        assert assumption.confidence is not None
        assert 0.0 <= assumption.confidence <= 1.0
        assert assumption.status == "inferred"
        assert assumption.source == "rule_based_inference"
        assert assumption.role_type is not None
        assert assumption.column_name is not None


def test_columns_are_not_assigned_to_every_role_bucket() -> None:
    df = pd.read_csv("tests/fixtures/role_inference/ambiguous_sample.csv")
    result = infer_column_roles(df)

    role_sets = [
        _columns(result.key_candidates),
        _columns(result.date_candidates),
        _columns(result.numeric_measure_candidates),
        _columns(result.categorical_candidates),
    ]

    intersection = set.intersection(*role_sets) if all(role_sets) else set()
    assert intersection == set()


def test_date_and_categorical_recognition_on_ambiguous_fixture() -> None:
    df = pd.read_csv("tests/fixtures/role_inference/ambiguous_sample.csv")
    result = infer_column_roles(df)

    assert "snapshot_dt" in _columns(result.date_candidates)
    assert "desk" in _columns(result.categorical_candidates)
