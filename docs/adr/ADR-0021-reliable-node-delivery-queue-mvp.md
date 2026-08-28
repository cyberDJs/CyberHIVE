# ADR-0021 — Reliable Node Delivery Queue MVP

## Status

Accepted

## Context

Secure Node Gateway can sign and verify messages, but outbound controller actions still lack delivery state. Without a queue, CyberHIVE cannot distinguish between "message created", "message dispatched", "node acknowledged it", "retry pending", and "dead-lettered".

## Decision

Add an in-memory reliable delivery queue with explicit lifecycle states, retry/backoff policy, ACK correlation, TTL expiry, and dead-letter handling.

The MVP integrates with `SecureNodeGateway` but does not implement a network transport or durable storage.

## Consequences

- Controller-to-node actions now have an auditable delivery lifecycle.
- Future transports can drain the queue without redesigning policy/gateway contracts.
- ACKs can be correlated by delivery id, correlation id, ack target, or envelope id.
- Queue state is still memory-only and must not be treated as production durability.
