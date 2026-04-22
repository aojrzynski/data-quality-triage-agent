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

## Milestone 3 — Agent-readiness structure (this stage)
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

## Milestone 4 — Rule-based intake and assumptions (planned)
- tabular suitability checks
- sheet/table selection heuristics
- initial column-role inference scaffolding
- assumption capture with confidence and status

Acceptance criteria:
- intake produces explicit assumptions
- assumptions can be auto-accepted and surfaced for future confirmation flows

## Milestone 5 — Rule-based planner/executor (planned)
- initial agent-mode action loop (rule-based, not LLM-first)
- dynamic deterministic tool selection
- action history + stop-condition handling

Acceptance criteria:
- agent mode runs a real, inspectable sequence of actions
- deterministic tools remain the source of truth for issue detection

## Milestone 6 — Investigation and triage output (planned)
- follow-up investigation actions
- stop rationale and triage-style conclusions
- separate triage narrative reporting path

Acceptance criteria:
- agent mode produces a clear triage conclusion with traceable action history

## Milestone 7 — Optional human-in-the-loop + polish (planned)
- user confirmation/override for critical assumptions
- optional LLM polish for summaries/plans (still non-authoritative)

Acceptance criteria:
- users can inspect and override assumptions
- LLM remains optional and bounded by deterministic evidence
