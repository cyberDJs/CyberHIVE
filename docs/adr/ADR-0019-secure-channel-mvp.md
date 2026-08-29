# ADR-0019 — Secure Channel MVP

## Status

Accepted

## Context

By Patch 016, nodes can be discovered and enrolled. Patch 015 accepts authenticated heartbeats through session verification, and Patch 013 defines node action dispatch. The next missing boundary is a structured message envelope that can be verified before any heartbeat or action payload is processed.

## Decision

Introduce a dependency-free Secure Channel MVP based on canonical signed envelopes.

The channel will:

- sign message envelopes with HMAC-SHA256 using node session tokens,
- verify active sessions through `NodeIdentityRegistry`,
- enforce expected direction and purpose,
- reject stale, expired, future-skewed, unsigned and tampered messages,
- reject replayed sequences and repeated message digests,
- expose optional adapters for heartbeat ingestion and action dispatch.

## Consequences

Positive:

- The controller gets a single verification boundary for node messages.
- Future transports can reuse the same envelope semantics.
- Replay protection is explicit and testable.
- The system remains local and dependency-free.

Negative:

- HMAC session tokens are not a replacement for mTLS or device PKI.
- Payloads are authenticated but not encrypted.
- Sequence state is in memory only.

## Non-goals

- Opening sockets.
- Implementing TLS/mTLS.
- Implementing node remote execution.
- Persisting channel state.
- Encrypting payload bodies.
