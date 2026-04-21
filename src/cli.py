"""CLI entry point for the Data Quality Triage Agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.checks import run_checks
from src.io import load_csv, save_json, save_markdown
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
    return parser.parse_args()


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


if __name__ == "__main__":
    main()