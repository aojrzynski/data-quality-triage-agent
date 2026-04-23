# Project Scope: Data Quality Triage Agent

## What this repository is today
This repository is currently a **deterministic local data quality triage tool** with an optional LLM explanation layer.

Today it can:
- Run deterministic intake (file format awareness, tabular suitability assessment, XLSX sheet selection).
- Run deterministic role inference to produce structured assumptions (key/date/numeric/categorical candidates with confidence/provenance).
- Load CSV and XLSX files locally via CLI.
- Build a dataset profile.
- Run deterministic checks (schema surprises, missing values, duplicate keys, unexpected categories, date gaps, numeric outliers).
- Score findings and generate JSON + Markdown outputs.
- Optionally generate an LLM-written summary on top of deterministic findings.

## End goal
The long-term goal is a genuine **Data Quality Triage Agent** that can:
- Keep deterministic checks as the trusted detection foundation.
- Add a separate agent mode for planning, orchestration, and triage reasoning.
- Guide users through assumptions and follow-up investigation before reaching triage conclusions.

## Mode definitions

### Deterministic mode (current stable baseline)
Deterministic mode means:
- Static, predictable check execution.
- Config-driven rules and deterministic findings.
- No autonomous planning loop.
- Role assumptions are inferred and surfaced, but not yet user-confirmed/overridden.
- Same behavior for the same input/config.

This mode is intended to remain stable and backward compatible.

### Agent mode (Stage 7 implementation)
Agent mode currently means:
- Explicit orchestration/planning steps (rule-based planner/executor).
- Assumption tracking (inferred assumptions recorded in run state).
- Assumption-driven role-to-tool binding resolution (override -> inferred -> config fallback).
- Dynamic deterministic tool invocation against resolved columns, with inspectable action history.
- Explicit stop conditions and stop rationale capture.
- Categorical validation only where selected columns have configured categorical rule sets; otherwise actions are explicitly skipped and traced.
- Future work: iterative investigation and triage-style conclusions.

## In scope
- Local-first operation.
- CLI-first UX.
- Deterministic checks as source of truth.
- Optional LLM usage only for planning/explanation/polish (not primary issue detection).
- Incremental implementation toward agent mode.

## Out of scope
- Replacing deterministic checks with LLM-only detection.
- Web app implementation.
- Database-backed architecture.
- Framework rewrite.
- “One-shot” full autonomous agent implementation in a single refactor.

## Compatibility commitment
A core commitment of this project is that **deterministic mode remains supported** while agent mode is introduced incrementally.
Any future agent capabilities should layer on top of (not replace) deterministic reliability.
