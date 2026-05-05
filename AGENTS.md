# Contributor and Coding-Agent Guidance

## Project guardrails

- Preserve deterministic mode behavior.
- Keep LLM usage optional and non-authoritative.
- Keep agent mode bounded, rule-based, and traceable.
- Do not introduce web frameworks, databases, or major architecture rewrites unless explicitly requested.

## Change strategy

- Prefer small, focused modules and incremental edits.
- Avoid broad refactors during polish tasks.
- Keep deterministic artifacts inspectable.
- Preserve clear mode boundaries in `src/cli.py`.

## Testing and validation

- Add or update tests for behavior changes.
- Run `python -m pytest` before finishing.
- Keep existing tests unless there is a clear reason to replace them.

## Documentation discipline

- Update docs when architecture or CLI behavior changes.
- Keep terminology consistent: deterministic mode, agent mode, intake, assumptions, resolved bindings, planner, deterministic tools, investigations, trace, agent report, LLM-polished report.
- Write plain technical English; avoid hype language.
