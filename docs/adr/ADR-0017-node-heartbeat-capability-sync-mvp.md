# ADR-0017: Node Heartbeat & Capability Sync MVP

## Status

Accepted

## Context

CyberHIVE can now enroll nodes and dispatch typed node actions, but the scheduler still needs a fresh view of node capacity, capabilities, queue pressure and data locality.

## Decision

Introduce a controller-side `NodeHeartbeatStore` that accepts authenticated `NodeHeartbeat` samples, derives `CapabilitySnapshot` records, computes liveness, and can sync scheduler `NodeState` objects into `ComputeRouter`.

## Consequences

Positive:

- routing can be based on fresh telemetry,
- stale nodes can be detected,
- capabilities can be updated through heartbeat snapshots,
- node identity/session checks protect ingestion from anonymous LAN noise.

Trade-offs:

- storage remains in-memory,
- no network transport yet,
- no automatic node quarantine yet,
- liveness thresholds are simple fixed values.
