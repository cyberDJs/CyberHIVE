# ADR-0006: Adaptive Data Fabric MVP

## Status

Accepted for MVP.

## Context

CyberHIVE will handle model weights, observations, runtime logs, cached
artifacts, embeddings, media, datasets, documents and build outputs. Treating
all data as equal causes wasted I/O, network traffic and latency.

Cloud storage products often encourage billing-driven architecture. CyberHIVE
should instead optimize for system behavior: where data should live for the
workload at hand.

## Decision

Implement an Adaptive Data Fabric MVP with:

- explicit storage tiers from RAM to archive,
- data object metadata,
- access observation records,
- derived data profiles,
- temperature scoring,
- placement decisions,
- migration plans,
- security-aware handling for sensitive and secret data.

The MVP avoids direct monetary pricing in the placement score.

## Consequences

Positive:

- better runtime locality,
- fewer repeated transfers,
- foundation for prefetch and predictive scheduling,
- cheaper operation as a side effect of better resource use,
- clear path toward safe automatic data movement.

Negative:

- more metadata must be maintained,
- access observations must be retained carefully,
- wrong predictions can cause unnecessary movement,
- actual file moving still needs a safe implementation.

## Follow-up

Add a Data Mover with:

- dry-run output,
- checksum verification,
- copy-then-switch semantics,
- rollback plan,
- Runtime Bus observation emission,
- policy checks before moving sensitive data.
