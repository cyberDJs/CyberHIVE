# Patch 010 — Execution Engine MVP

## Purpose

Patch 010 adds the first safe execution layer for CyberHIVE orchestration plans.

Patch 009 produced auditable plans. This patch turns those plans into auditable
execution runs without introducing remote execution, destructive data movement or
durable distributed workflow complexity.

## Added

- `ExecutionEngine`
- `ExecutionRun`
- `ExecutionStepResult`
- `ExecutionJournal`
- `ExecutionPolicy`
- Runtime Bus event publishing for plan lifecycle
- execution run JSON schema
- validation script
- demo script
- unit tests
- ADR `ADR-0012-execution-engine-mvp.md`

## Behavior

The MVP executor:

1. validates an `OrchestrationPlan`,
2. produces a dry-run or local execution run,
3. records step-level results,
4. refuses unsafe physical side effects by default,
5. can publish `execution.started` and `execution.completed` events to the
   Runtime Bus,
6. can append runs to a local JSONL journal.

Physical data movement, remote execution and arbitrary shell commands remain
outside the default execution path. They require explicit later handlers and
policy gates.

## Validation

```bash
PYTHONPATH=src python3 scripts/validate_execution_engine_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_execution_engine.py
```
