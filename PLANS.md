# Implementation Plan

This roadmap describes milestones for evolving from deterministic triage tool to full Data Quality Triage Agent.

## Milestone 1 — Stable deterministic baseline (completed)
- CSV/XLSX loading
- deterministic checks + scoring
- JSON + Markdown outputs
- fixture-driven validation

Acceptance criteria:
- deterministic CLI runs reliably on sample data
- tests verify deterministic checks and expected fixtures

## Milestone 2 — Optional explanation layer (completed)
- optional LLM summary generation
- deterministic findings remain authoritative

Acceptance criteria:
- LLM summary is optional and layered on top of deterministic outputs

## Milestone 3 — Agent-readiness structure (completed)
- add canonical scope/architecture/plan docs
- add explicit CLI mode boundary (`deterministic` vs `agent`)
- extract expected-result comparison from CLI
- add thin deterministic tool interface metadata/wrappers
- add agent-state scaffolding
- prepare reporting separation for future triage narrative

Acceptance criteria:
- deterministic behavior remains compatible
- `--mode agent` is explicit and honestly not implemented
- architecture supports future orchestration work without a rewrite

## Milestone 4 — Intake + sheet selection foundations (completed)
- tabular suitability checks
- sheet/table selection heuristics
- structured intake outputs for future role inference/planning

Acceptance criteria:
- intake is explicit, deterministic, and testable
- XLSX default sheet selection is stronger than sheet index 0
- suitability signals are surfaced clearly before checks

## Milestone 5 — Role inference + assumptions (completed)
- deterministic, rule-based inference for key/date/numeric/categorical candidates
- structured assumption objects with confidence, provenance, and status
- CLI surfacing of inferred assumptions before checks
- assumption capture scaffold for inferred vs confirmed vs overridden

Acceptance criteria:
- role assumptions are explicit and inspectable
- deterministic tools remain the source of truth for issue detection

## Milestone 6 — Rule-based planner/executor (completed)
- initial agent-mode action loop (rule-based, not LLM-first)
- dynamic deterministic tool selection
- action history and stop-condition handling

Acceptance criteria:
- planner/executor behavior is inspectable and deterministic-first
- agent mode runs a traceable sequence of actions over deterministic tools

## Milestone 7 — Assumption-driven execution binding (completed)
- add explicit assumption-to-tool binding resolver for agent mode
- support agent-only non-interactive override flags for role columns
- execute role-bound tools on resolved columns (not only static config columns)
- record resolved bindings/binding sources in trace and action details
- explicit skip handling for unavailable bindings and missing categorical rule sets

Acceptance criteria:
- deterministic mode remains stable and config-driven
- agent mode executes role-bound tools against inferred or overridden columns
- trace output explains bound columns, binding source, and skips

## Milestone 8 — Investigation and triage output (planned)
- follow-up investigation actions
- stop rationale and triage-style conclusions
- separate triage narrative reporting path

Acceptance criteria:
- agent mode produces a clear triage conclusion with traceable action history

## Milestone 9 — Optional human-in-the-loop + polish (planned)
- user confirmation/override for critical assumptions
- optional LLM polish for summaries/plans (still non-authoritative)

Acceptance criteria:
- users can inspect and override assumptions
- LLM remains optional and bounded by deterministic evidence
