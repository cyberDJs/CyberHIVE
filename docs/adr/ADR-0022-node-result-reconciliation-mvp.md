# ADR-0022: Node Result Reconciliation MVP

## Status

Accepted

## Context

CyberHIVE now has secure channels, a secure node gateway and reliable delivery. The controller can dispatch signed action messages and track ACK/dead-letter state. However, delivery ACK is not equivalent to action completion. Node action results and errors need a separate reconciliation step before they influence execution/run state.

## Decision

Introduce `NodeResultReconciler` as a pure controller-side projection layer.

The reconciler:

- registers `DeliveryItem` records,
- accepts verified `GatewayReceipt` objects,
- correlates ACK/ACTION_RESULT/ERROR payloads,
- records append-only task history,
- creates orphan records for unmatched results,
- projects per-run/per-plan summaries.

## Consequences

Positive:

- ACK and result semantics stay separate.
- Orphaned node messages are visible instead of silently discarded.
- Execution UI/API can consume a single task projection.
- Later persistence can store reconciliation records without changing node protocol semantics.

Negative:

- It adds another state machine.
- The MVP is in-memory and must be backed by durable storage later.
- It depends on consistent correlation IDs across gateway/delivery/agent layers.

## Security notes

The reconciler does not accept raw network messages. It only consumes receipts produced by the secure gateway. This prevents duplicate signature/replay logic and keeps responsibilities separate.

## Follow-ups

- Durable reconciliation store.
- Execution run state integration.
- Operator-facing CLI/API for pending/orphaned/dead-letter tasks.
- Metrics for ACK latency and result latency.
