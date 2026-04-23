from pathlib import Path

import pandas as pd

from src.intake import assess_tabular_suitability, inspect_and_select_dataset


def test_csv_intake_is_single_candidate() -> None:
    result = inspect_and_select_dataset("sample_data/clean/orders_clean.csv")

    assert result.file_type == "csv"
    assert result.selection_mode == "single"
    assert result.selected_sheet_name is None
    assert len(result.candidates) == 1
    assert result.selected_candidate.suitability.status == "suitable"


def test_assess_tabular_suitability_flags_weak_dataset() -> None:
    weak_df = pd.read_csv("tests/fixtures/intake/mostly_blank.csv")

    suitability = assess_tabular_suitability(weak_df)

    assert suitability.status == "unsuitable"
    assert suitability.score < 40
    assert suitability.recommended_action


def test_assess_tabular_suitability_hard_fails_empty_rows() -> None:
    empty_df = pd.read_csv("tests/fixtures/intake/empty_columns.csv")

    suitability = assess_tabular_suitability(empty_df)

    assert suitability.status == "unsuitable"
    assert suitability.hard_failure is True


def test_xlsx_auto_selection_picks_stronger_tabular_sheet(tmp_path: Path) -> None:
    workbook_path = tmp_path / "candidate_workbook.xlsx"

    strong_sheet = pd.DataFrame(
        {
            "order_id": [1, 2, 3, 4],
            "status": ["pending", "shipped", "delivered", "cancelled"],
            "amount": [10.0, 11.5, 9.2, 12.1],
        }
    )
    weak_sheet = pd.DataFrame({"Unnamed: 0": [None, None, "x"], "Unnamed: 1": [None, None, None]})

    with pd.ExcelWriter(workbook_path) as writer:
        weak_sheet.to_excel(writer, sheet_name="Notes", index=False)
        strong_sheet.to_excel(writer, sheet_name="Orders", index=False)

    result = inspect_and_select_dataset(workbook_path)

    assert result.file_type == "xlsx"
    assert result.selection_mode == "auto"
    assert result.selected_sheet_name == "Orders"
    assert result.selected_candidate.suitability.status == "suitable"
    assert [c.candidate_id for c in result.candidates] == ["Orders", "Notes"]


def test_xlsx_explicit_sheet_is_respected(tmp_path: Path) -> None:
    workbook_path = tmp_path / "explicit_sheet.xlsx"

    with pd.ExcelWriter(workbook_path) as writer:
        pd.DataFrame({"good": [1, 2], "also_good": [3, 4]}).to_excel(
            writer,
            sheet_name="Data",
            index=False,
        )
        pd.DataFrame({"Unnamed: 0": [None, None]}).to_excel(
            writer,
            sheet_name="Cover",
            index=False,
        )

    result = inspect_and_select_dataset(workbook_path, sheet_name="Cover")

    assert result.selection_mode == "explicit"
    assert result.selected_sheet_name == "Cover"
    assert result.selected_candidate.candidate_id == "Cover"


def test_xlsx_explicit_sheet_index_surfaces_resolved_name(tmp_path: Path) -> None:
    workbook_path = tmp_path / "explicit_index.xlsx"

    with pd.ExcelWriter(workbook_path) as writer:
        pd.DataFrame({"cover": [None, None]}).to_excel(writer, sheet_name="Cover", index=False)
        pd.DataFrame({"order_id": [1, 2], "amount": [10, 20]}).to_excel(
            writer,
            sheet_name="Orders",
            index=False,
        )

    result = inspect_and_select_dataset(workbook_path, sheet_name=1)

    assert result.selection_mode == "explicit"
    assert result.selected_sheet_name == "Orders"
    assert result.selected_candidate.candidate_id == "Orders"
