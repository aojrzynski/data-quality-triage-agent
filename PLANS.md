# Roadmap and Future Work

This document describes practical next steps. It is not a build log.

## Near-term improvements

- Improve planner heuristics for borderline intake cases.
- Expand investigation summaries with clearer remediation hints.
- Add more edge-case fixtures for mixed-type and messy-header datasets.
- Improve CLI help text and validation errors for agent overrides.

## Medium-term improvements

- Add richer deterministic check families while keeping check contracts simple.
- Expand trace ergonomics for easier diffing across runs.
- Add lightweight benchmark fixtures to track performance drift.

## Longer-term ideas

- Bounded adaptive replanning based on first-pass findings.
- Additional input adapters (while preserving local-first behavior).
- Optional profile/report templates for different stakeholder audiences.

## Guardrails for all future work

- Keep deterministic mode stable.
- Keep LLM usage optional and non-authoritative.
- Keep agent mode bounded and inspectable.
- Prefer small modules and test-backed changes.
