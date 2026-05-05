# Project Scope

## Purpose

This repository is a local, CLI-based data quality triage project with two modes:

- **deterministic mode** for stable, config-driven checks,
- **agent mode** for rule-based orchestration of deterministic tools.

The project is intentionally educational: it favors inspectability, explicit trade-offs, and traceable behavior.

## Current capabilities

- Deterministic intake for CSV/XLSX inputs.
- XLSX sheet selection (explicit or auto-ranked).
- Deterministic role inference (`key`, `date`, `numeric_measure`, `categorical`).
- Assumption tracking and optional interactive confirmation.
- Resolved role-to-tool bindings with explicit precedence.
- Rule-based planning and deterministic tool execution.
- Bounded second-pass investigations.
- Deterministic reports and agent traces.
- Optional LLM-polished report artifact.

## Core principles

- Deterministic checks are the source of truth.
- Agent mode orchestrates; it does not replace deterministic detection.
- LLM usage is optional and non-authoritative.
- Outputs must be inspectable and reproducible.
- Local-first operation is preferred.

## In scope

- CLI-first workflows.
- Deterministic issue detection.
- Rule-based, bounded orchestration.
- Clear artifacts for debugging, teaching, and portfolio review.

## Out of scope

- LLM-only issue detection.
- Web application development.
- Database-backed architecture.
- Large framework migration.
- Claims of open-ended autonomous intelligence.
