# ADR-0025: Local Resource Guard MVP

## Status

Accepted for MVP implementation.

## Context

A signed action is not enough. The node must also decide whether it has safe local capacity before running a handler.

## Decision

Add `LocalResourceGuard` with static in-memory CPU/RAM/VRAM/IO/concurrency budgets and resource reservations. Dry-run preflight does not consume capacity; live reservations do until released.

## Consequences

- Positive: worker runtime gains a local admission-control boundary.
- Positive: future cgroup/container enforcement can consume the same reservation model.
- Negative: no host metric sampling or kernel-level enforcement yet.
