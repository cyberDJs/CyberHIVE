# ADR-0023: Node Worker Runtime Loop MVP

## Status

Accepted for MVP implementation.

## Context

Patches 018-020 created secure gateway, reliable delivery, and result reconciliation. A node-side loop was needed to consume signed action envelopes and return ACK/result envelopes.

## Decision

Implement `NodeWorkerRuntime` as a deterministic in-memory runtime that verifies signed ACTION envelopes, emits ACK, performs guarded handler dispatch, and emits ACTION_RESULT.

## Consequences

- Positive: end-to-end controller/node lifecycle can now be tested without network transport.
- Positive: ACK and action success remain separate.
- Negative: no real daemon, socket, sandbox, or subprocess execution yet.
