"""CLI entry point for the Data Quality Triage Agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.checks import run_checks
from src.config import load_agent_config
from src.expected_validation import compare_to_expected
from src.io import load_dataset, load_json, save_json, save_markdown
from src.llm_summary import generate_llm_summary
from src.models import RunResult
from src.profiling import build_dataset_profile, dataset_name_from_path
from src.reporting import build_markdown_report
from src.scoring import score_findings


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the Data Quality Triage Agent.")
    parser.add_argument("--input", required=True, help="Path to the input dataset file.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for outputs.")
    parser.add_argument("--expected", help="Optional expected-results JSON fixture.")
    parser.add_argument(
        "--config",
        default="config/default_config.json",
        help="Path to the config JSON file.",
    )
    parser.add_argument(
        "--sheet",
        default="0",
        help="Excel sheet name or sheet index (used only for .xlsx files). Default is 0.",
    )
    parser.add_argument(
        "--mode",
        choices=["deterministic", "agent"],
        default="deterministic",
        help="Execution mode. Deterministic mode is stable; agent mode is planned.",
    )
    parser.add_argument(
        "--llm-summary",
        action="store_true",
        help="Generate an optional LLM-written summary using the OpenAI API.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model override for the LLM summary.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the current version of the agent."""
    args = parse_args()

    if args.mode == "agent":
        print("Agent mode is not implemented yet.")
        print(
            "Use --mode deterministic (or omit --mode) to run the stable deterministic checks."
        )
        raise SystemExit(2)

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    sheet_arg: str | int
    if args.sheet.isdigit():
        sheet_arg = int(args.sheet)
    else:
        sheet_arg = args.sheet

    dataset_name = dataset_name_from_path(input_path)
    config = load_agent_config(args.config)

    df = load_dataset(input_path, sheet_name=sheet_arg)
    profile = build_dataset_profile(df=df, dataset_name=dataset_name)

    findings = run_checks(df, config=config)
    scored_findings = score_findings(findings)

    run_result = RunResult(
        dataset_name=dataset_name,
        profile=profile,
        findings=scored_findings,
    )

    llm_summary = None
    if args.llm_summary:
        llm_summary = generate_llm_summary(run_result, model=args.model)

    json_output_path = output_dir / f"{input_path.stem}_profile.json"
    markdown_output_path = output_dir / f"{input_path.stem}_report.md"

    save_json(json_output_path, run_result.to_dict())
    save_markdown(markdown_output_path, build_markdown_report(run_result, llm_summary=llm_summary))

    if llm_summary:
        llm_summary_path = output_dir / f"{input_path.stem}_llm_summary.md"
        save_markdown(llm_summary_path, llm_summary)

    print("Data Quality Triage Agent")
    print(f"Mode: {args.mode}")
    print(f"Loaded dataset: {dataset_name}")
    print(f"Config: {args.config}")
    print(f"Rows: {profile.row_count}")
    print(f"Columns: {profile.column_count}")
    print(f"Findings: {len(scored_findings)}")
    print(f"JSON output: {json_output_path}")
    print(f"Markdown output: {markdown_output_path}")

    if llm_summary:
        print(f"LLM summary: {output_dir / f'{input_path.stem}_llm_summary.md'}")

    if scored_findings:
        print("\nDetected findings:")
        for finding in scored_findings:
            print(f"- [{finding.severity.upper()}] {finding.finding_type} ({finding.column})")

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
