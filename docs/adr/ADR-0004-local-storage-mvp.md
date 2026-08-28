# ADR-0004: Storage MVP separates hot runtime state from durable metadata

## Status

Accepted for MVP.

## Context

CyberHIVE should not treat every event as a relational database transaction.
High-frequency observations and state deltas need a cheaper write path, while
identity, inventory, policies and audit indexes still need durable structured
metadata.

## Decision

Patch 002 implements only local MVP primitives:

- hot state in memory via `StateEngine`,
- runtime event trail in append-only JSONL,
- cache as in-memory fabric,
- data placement as recommendation engine.

No production database is introduced yet.

## Consequences

Positive:

- zero external services for local experimentation,
- fast feedback loop,
- keeps future backend choices open.

Negative:

- no multi-process coordination,
- no crash-safe transaction boundaries beyond append-only frame writes,
- no long-term retention policy yet.

## Follow-up

Choose local durable KV and relational metadata stores only after measuring the
MVP workload.
