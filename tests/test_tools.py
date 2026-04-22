from src.config import load_agent_config
from src.io import load_csv
from src.scoring import score_findings
from src.tools import list_deterministic_tools, run_deterministic_tools


def test_tool_registry_contains_expected_tools() -> None:
    tool_names = [tool.name for tool in list_deterministic_tools()]
    assert tool_names == [
        "schema_surprises",
        "missing_values",
        "duplicate_keys",
        "unexpected_categorical_values",
        "date_gaps",
        "numeric_outliers",
    ]


def test_run_deterministic_tools_matches_run_checks_for_clean_data() -> None:
    df = load_csv("sample_data/clean/orders_clean.csv")
    config = load_agent_config()

    findings = run_deterministic_tools(df, config=config)
    scored = score_findings(findings)

    assert findings == []
    assert scored == []


def test_run_deterministic_tools_finds_known_issues() -> None:
    df = load_csv("sample_data/broken/orders_bad_categories.csv")
    config = load_agent_config()

    findings = score_findings(run_deterministic_tools(df, config=config))

    matching = [
        finding
        for finding in findings
        if finding.finding_type == "unexpected_values" and finding.column == "status"
    ]
    assert len(matching) == 1
    assert matching[0].severity == "medium"
