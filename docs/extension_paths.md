# Extension Paths

This repo can be extended in three main places.

## 1. Deterministic checks

Add more checks where the result should be repeatable and testable.

Examples:

- freshness checks
- referential integrity checks
- cross-file reconciliation
- stricter schema validation
- business-specific rules

This is the right layer for logic that should not depend on an LLM.

## 2. Agent orchestration

Change how the agent plans, investigates, and stops.

Examples:

- better planner heuristics
- deeper second-pass investigations
- bounded replanning
- better assumption confirmation
- different stop conditions

This is the right layer for experimenting with agent behaviour.

## 3. LLM layer

Expand the optional LLM layer.

Examples:

- better final report polish
- questions about the trace
- explanations of skipped checks
- stakeholder-specific summaries

The LLM layer should stay non-authoritative unless the project goals change. It can explain evidence, but the deterministic checks produce the evidence.