# ADR-0012: Execution Engine MVP

## Status

Accepted

## Context

Patch 009 introduced `IntegrationOrchestrator`, which composes cache, data,
forecasting and routing decisions into one `OrchestrationPlan`. The next layer
needs to convert that plan into a traceable execution record.

Executing immediately and physically would be risky because several CyberHIVE
subsystems are still MVPs. In particular, data movement and node execution need
policy gates, durable recovery and rollback semantics.

## Decision

Add an `ExecutionEngine` that executes plans only in a safe local MVP sense:

- creates `ExecutionRun` records,
- supports dry-run and non-destructive local completion,
- publishes lifecycle events to Runtime Bus when provided,
- writes optional append-only JSONL journal entries,
- skips physical side-effect steps by default.

## Consequences

Positive:

- CyberHIVE now has plan → run lifecycle semantics,
- execution is auditable and testable,
- future remote execution gets a safe integration seam,
- dry-run remains the default operational posture.

Negative:

- no real remote compute execution yet,
- no physical data movement from orchestration moves yet,
- no retry/backoff/lease model yet.

## Follow-up

- add handler registry with explicit policy gates,
- add durable retry model,
- connect DataMover execution with object path registry,
- add worker-node execution adapter,
- add rollback coordinator.
