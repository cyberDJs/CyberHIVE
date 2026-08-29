# CyberHIVE Execution Engine MVP

## Decision

CyberHIVE needs a controlled execution layer after the Integration Orchestrator.
The orchestrator decides what should happen; the Execution Engine records what
was attempted, what was skipped, and what completed.

The MVP is deliberately conservative. It does **not** run arbitrary shell
commands, does **not** move data by default and does **not** call remote nodes.
It creates an auditable execution run from an orchestration plan.

## Flow

```text
OrchestrationPlan
  ↓
ExecutionEngine
  ↓
ExecutionRun
  ↓
Runtime Bus events + optional JSONL journal
```

## Safety model

- Dry-run is first-class.
- Physical side effects are disabled by default.
- Unknown or external steps are skipped unless a future handler is registered.
- Runtime Bus publication is structured and non-destructive.
- Journal entries are append-only JSON lines.

## What executes in MVP

| Plan step | Default behavior |
|---|---|
| `reuse` | recorded as completed/skipped based on plan state |
| `data_placement` | recorded as planned |
| `data_moves` | skipped unless future policy allows handlers |
| `scheduler_hints` | recorded as applied to decision context |
| `route` | recorded as route decision accepted |
| `prewarm` | recorded as planned, not physically executed |

## Non-goals

- remote worker execution,
- DAG engine,
- retries with distributed leases,
- arbitrary command execution,
- Kubernetes controller,
- automatic physical data movement.

Those belong after the execution journal, policy gates and rollback semantics are
stable.
