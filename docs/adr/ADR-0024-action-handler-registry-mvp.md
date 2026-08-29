# ADR-0024: Action Handler Registry MVP

## Status

Accepted for MVP implementation.

## Context

A single node agent dispatcher is too rigid for future local actions. CyberHIVE needs a registry that resolves typed actions to explicit handlers while failing closed for unknown work.

## Decision

Add `ActionHandlerRegistry` with explicit handler metadata, dry-run/live-safety flags, and a compatibility adapter for `LocalNodeAgent`.

## Consequences

- Positive: new node actions can be added without changing the worker loop.
- Positive: live-safety is explicit at handler registration.
- Negative: handler registration is in-memory only.
