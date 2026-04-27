# Architecture

## Purpose
This document describes both:
1. The current architecture in the repository.
2. The target layered architecture needed to support future agent mode safely.

The design principle is incremental evolution: preserve deterministic reliability while adding clean boundaries for orchestration.

## Current architecture (Stage 9 baseline)

### 1) Input and normalization layer
- `src/io.py`: file loading/saving utilities (CSV/XLSX, JSON/Markdown output).
- `src/intake.py`: deterministic intake (file-type awareness, suitability scoring, XLSX sheet ranking/selection).
- `src/profiling.py`: dataset profiling and dataset naming.
- `src/role_inference.py`: deterministic role inference and structured assumption generation.
- `src/config.py`: deterministic check configuration loading.

### 2) Deterministic tool layer
- `src/checks.py`: deterministic finding logic.
- `src/scoring.py`: severity scoring/ranking.
- `src/tools.py`: thin metadata + wrappers for deterministic checks (for future orchestration reuse).

### 3) Orchestration / execution boundary
- `src/cli.py`:
  - explicit mode boundary via `--mode deterministic|agent`
  - deterministic execution path remains stable
  - agent mode runs rule-based planning/execution and optional interactive assumption confirmation (`--confirm-assumptions`)
- `src/planner.py`: rule-based selection of deterministic tool sequence.
- `src/bindings.py`: explicit assumption-to-tool binding resolution (CLI override/interactively confirmed override/inferred/config fallback).
- `src/agent_runner.py`: executor loop + optional assumption confirmation + resolved bindings + status propagation + action history + bounded investigation pass + stop rationale + trace/report artifacts.
- `src/investigation_tools.py`: deterministic follow-up investigation helpers for key finding families.

### 4) Reporting and output layer
- `src/reporting.py`: deterministic Markdown report generation.
- `src/expected_validation.py`: expected-fixture validation logic extracted from CLI.
- `src/triage_reporting.py`: deterministic triage summary + agent markdown report generation.

### 5) Optional LLM layer
- `src/llm_summary.py`: optional summary generation using deterministic outputs.
- LLM is non-authoritative and additive.

## Target architecture (incremental)

### Layer A: Intake + suitability (implemented foundation)
Responsibilities:
- detect whether input is tabular and suitable for deterministic tools
- choose sheet/table where relevant
- return structured candidate summaries for future agent assumptions/planning

Output:
- validated intake context for deterministic execution today and planner/executor later

### Layer B: Deterministic assumptions + tools (source of truth remains tools)
Responsibilities:
- infer likely column roles using deterministic heuristics
- emit inspectable assumptions with confidence/provenance
- keep check execution config-driven in deterministic mode

Output:
- assumption candidates that future confirmation/planning layers can consume

### Layer C: Deterministic tools (existing source of truth)
Responsibilities:
- deterministic, reproducible checks
- structured findings

Output:
- trustworthy findings that planner can inspect and reference

### Layer D: Agent orchestration (in progress)
Responsibilities:
- rule-based planner/executor
- resolve and record role-to-tool bindings before execution
- track assumptions, confidence, and status transitions (`inferred`, `auto_accepted`, `user_confirmed`, `user_overridden`)
- optionally collect per-role user confirmation/override via CLI prompt
- choose which tools to run and when to stop
- trigger bounded second-pass investigations from deterministic findings

Output:
- resolved bindings + action history + investigation evidence + stop rationale + triage conclusions

### Layer E: Reporting (split by mode)
Responsibilities:
- deterministic report path remains stable
- agent mode emits deterministic triage summary/report output separately

Output:
- deterministic report (`reporting.py`) and future triage report (`triage_reporting.py`)

## LLM boundaries
LLM may assist with:
- explanation/polish of deterministic results
- future planning support (non-authoritative)

LLM must not become:
- primary detector of data quality issues
- replacement for deterministic check outputs

## Relationship between loaders, tools, and future planner
- Loaders and profiling establish standardized context.
- Deterministic tools provide reliable signals.
- Future planner will orchestrate tool usage and investigation using that context/signals.
- Reporting consumes the resulting state/output objects.

This keeps responsibilities clear and lets agent mode evolve safely without destabilizing deterministic runs.
