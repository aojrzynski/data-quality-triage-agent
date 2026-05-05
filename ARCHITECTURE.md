# Architecture

## Design intent

The architecture keeps issue detection deterministic and isolates orchestration concerns so agent behavior stays bounded and traceable.

## Layered view

1. **Input and intake layer**
   - `src/io.py`: dataset + artifact I/O.
   - `src/intake.py`: suitability scoring, candidate summaries, sheet selection.

2. **Inference and binding layer**
   - `src/role_inference.py`: deterministic role inference.
   - `src/bindings.py`: resolved role bindings (override -> confirmation -> inference -> fallback).

3. **Deterministic detection layer**
   - `src/checks.py`: check implementations.
   - `src/tools.py`: tool wrappers and metadata for planner/executor use.

4. **Orchestration layer (agent mode)**
   - `src/planner.py`: rule-based planning.
   - `src/agent_runner.py`: execution loop, assumption handling, investigations, trace.
   - `src/investigation_tools.py`: bounded follow-up evidence collection.

5. **Reporting layer**
   - `src/reporting.py`: deterministic mode markdown report.
   - `src/triage_reporting.py`: deterministic agent triage report.

6. **Optional LLM polish layer**
   - `src/llm_summary.py`: optional narrative rewrite from deterministic artifacts.

## Mode boundary

- `src/cli.py` provides an explicit `--mode deterministic|agent` boundary.
- Deterministic mode remains stable and config-driven.
- Agent mode remains rule-based and bounded (no deep adaptive replanning).

## Reliability boundaries

- Deterministic artifacts are canonical evidence.
- LLM outputs are optional polish artifacts only.
- Agent trace captures planning, action execution, investigation, and stop rationale.
