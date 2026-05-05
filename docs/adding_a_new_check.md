# Adding a New Deterministic Check

This guide shows how to add a check without breaking architecture boundaries.

## 1) Add check logic in `src/checks.py`

- Implement a deterministic function.
- Input should be explicit (`df` + required params).
- Return `list[Finding]` with clear `finding_type`, `severity`, `column`, and `message`.
- Keep this logic independent from planner/executor concerns.

## 2) Keep findings structured and stable

- Use consistent `finding_type` naming.
- Prefer deterministic counts and evidence fields.
- Avoid embedding non-deterministic text.

## 3) Ensure scoring behavior is appropriate

- If needed, update scoring rules in `src/scoring.py` so severity and ranking match project conventions.

## 4) Expose through `src/tools.py`

- Add a tool wrapper that calls the new deterministic check.
- Register metadata (`ToolSpec`) so planner/executor can reason about it.
- Keep wrappers thin so deterministic check behavior stays transparent.

## 5) Integrate with planner/bindings when relevant

- If the check depends on semantic roles (key/date/numeric/categorical), add or reuse binding behavior in `src/bindings.py`.
- Update `src/planner.py` to include the tool under clear rule-based conditions.
- If role-dependent, prefer resolved bindings over ad-hoc column guessing inside the tool path.

## 6) Add tests

At minimum, add or update:

- check-level tests for happy path and edge cases,
- tool-level tests if wrapper behavior changes,
- planner/agent tests if the new check is agent-invoked,
- expected-fixture tests when output expectations change.

## 7) Validate from CLI

Run representative deterministic and agent mode commands and confirm artifacts are correct and traceable.

## Why this separation exists

- Deterministic checks are the evidence source.
- Agent orchestration decides *when* and *where* to run checks, not *what the checks mean*.
- Optional LLM polish should summarize deterministic artifacts, never replace them.
