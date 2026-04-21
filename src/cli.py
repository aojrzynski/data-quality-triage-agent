"""CLI entry point for the Data Quality Triage Agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.checks import run_checks
from src.io import load_csv, load_json, save_json, save_markdown
from src.models import RunResult
from src.profiling import build_dataset_profile, dataset_name_from_path
from src.reporting import build_markdown_report
from src.scoring import score_findings


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the Data Quality Triage Agent.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where output files will be written.",
    )
    parser.add_argument(
        "--expected",
        help="Optional path to an expected-results JSON fixture.",
    )
    return parser.parse_args()


def compare_to_expected(
    run_result: RunResult,
    expected_payload: dict,
) -> list[str]:
    """Compare actual findings to an expected-results fixture."""
    messages: list[str] = []
    expected_findings = expected_payload.get("expected_findings", [])

    actual_by_type_and_column = {
        (finding.finding_type, finding.column): finding
        for finding in run_result.findings
    }

    for expected in expected_findings:
        key = (expected["type"], expected.get("column"))
        actual = actual_by_type_and_column.get(key)

        if actual is None:
            messages.append(
                f"Missing expected finding: type={expected['type']}, column={expected.get('column')}"
            )
            continue

        expected_severity = expected.get("severity")
        if expected_severity and actual.severity != expected_severity:
            messages.append(
                f"Severity mismatch for {key}: expected {expected_severity}, got {actual.severity}"
            )

        expected_min_count = expected.get("min_count")
        if expected_min_count is not None:
            actual_missing_count = int(actual.evidence.get("missing_count", 0))
            if actual_missing_count < expected_min_count:
                messages.append(
                    f"Missing count too low for {key}: expected at least {expected_min_count}, got {actual_missing_count}"
                )

        expected_values = expected.get("unexpected_values")
        if expected_values is not None:
            actual_values = actual.evidence.get("unexpected_values", [])
            if sorted(actual_values) != sorted(expected_values):
                messages.append(
                    f"Unexpected values mismatch for {key}: expected {expected_values}, got {actual_values}"
                )

    return messages


def main() -> None:
    """Run the current version of the agent."""
    args = parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    dataset_name = dataset_name_from_path(input_path)

    df = load_csv(input_path)
    profile = build_dataset_profile(df=df, dataset_name=dataset_name)

    findings = run_checks(df)
    scored_findings = score_findings(findings)

    run_result = RunResult(
        dataset_name=dataset_name,
        profile=profile,
        findings=scored_findings,
    )

    json_output_path = output_dir / f"{input_path.stem}_profile.json"
    markdown_output_path = output_dir / f"{input_path.stem}_report.md"

    save_json(json_output_path, run_result.to_dict())
    save_markdown(markdown_output_path, build_markdown_report(run_result))

    print("Data Quality Triage Agent")
    print(f"Loaded dataset: {dataset_name}")
    print(f"Rows: {profile.row_count}")
    print(f"Columns: {profile.column_count}")
    print(f"Findings: {len(scored_findings)}")
    print(f"JSON output: {json_output_path}")
    print(f"Markdown output: {markdown_output_path}")

    if scored_findings:
        print("\nDetected findings:")
        for finding in scored_findings:
            print(
                f"- [{finding.severity.upper()}] {finding.finding_type}"
                f" ({finding.column})"
            )

    if args.expected:
        expected_payload = load_json(args.expected)
        comparison_messages = compare_to_expected(run_result, expected_payload)

        print("\nExpected-results check:")
        if comparison_messages:
            print("- FAIL")
            for message in comparison_messages:
                print(f"  - {message}")
        else:
            print("- PASS")


if __name__ == "__main__":
    main()