# ADR-0020 — Secure Node Gateway MVP

## Status

Accepted

## Context

Patch 017 introduced signed envelopes but callers still had to pass session tokens directly to the secure channel router. CyberHIVE needs an integration boundary that owns session credentials and exposes a simple message ingress/egress surface.

## Decision

Add `SecureNodeGateway` with an in-memory `SessionCredentialVault`. The gateway builds signed controller messages, receives signed node messages, verifies them through `SecureChannel`, and dispatches only to explicit local MVP components.

## Consequences

- Higher layers do not need to handle raw session tokens directly.
- Heartbeats/actions/results now share one auditable gateway receipt model.
- Secrets remain memory-only for MVP.
- Real transport and persistent secret storage remain future work.
