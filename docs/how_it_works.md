# How It Works

This walkthrough explains the full runtime flow from input file to output artifacts.

1. **Input file**
   - CLI accepts CSV or XLSX via `--input`.

2. **Intake**
   - Intake evaluates tabular suitability.
   - For XLSX, it ranks sheets and selects one (unless `--sheet` is provided).

3. **Role inference**
   - Deterministic heuristics infer likely `key`, `date`, `numeric_measure`, and `categorical` columns.
   - Output is an assumption set with confidence and provenance.

4. **Assumption confirmation (optional, agent mode)**
   - `--confirm-assumptions` allows per-role confirmation or override.
   - Non-interactive flags can also override role columns.

5. **Resolved bindings**
   - Agent mode resolves role-to-tool bindings using explicit precedence:
     `CLI override -> interactive confirmation -> inference -> config fallback`.
   - This step keeps orchestration predictable: the planner/executor uses one resolved binding view instead of re-interpreting assumptions at each step.

6. **Planning (agent mode)**
   - Planner builds a rule-based first-pass sequence.
   - Foundational checks run first; role-driven tools are added when bindings are available.

7. **Deterministic tool execution**
   - Tools call deterministic checks and return structured findings.
   - Categorical checks run only where rule sets exist.
   - Deterministic checks stay separate from orchestration so detection logic remains reproducible and testable.

8. **Investigations (agent mode)**
   - A bounded second pass collects targeted evidence for selected issue families.

9. **Triage reporting**
   - Agent mode produces deterministic triage summary + markdown report.
   - Deterministic mode produces profile + markdown report.

10. **Optional LLM polish**
    - If `--llm-summary` is set, an additional markdown artifact can be generated.
    - Deterministic artifacts remain the source of truth.
    - This keeps API failures low-risk: deterministic runs still complete and remain inspectable.
