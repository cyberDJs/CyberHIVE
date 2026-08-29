# ADR-0016: Node Enrollment & Identity MVP

## Status

Accepted

## Context

Patch 013 introduced local node agents and typed node actions. Before CyberHIVE
can use real workers, the controller needs an explicit identity boundary.

A node must not be allowed to self-declare a trusted identity without proof.

## Decision

Introduce an in-memory MVP with:

- bootstrap tokens,
- HMAC enrollment proof,
- public key fingerprints,
- node identity registry,
- trust states,
- short-lived session grants,
- conversion to node-agent descriptors.

## Consequences

Positive:

- Node identity becomes explicit and auditable.
- Duplicate node ids and fingerprints are rejected.
- Quarantine/revoke flows exist before live remote execution exists.
- Later mTLS/PKI/attestation can replace internals without changing higher-level concepts.

Tradeoffs:

- No persistent secure storage yet.
- No real asymmetric signing verification yet.
- No remote attestation yet.
- In-memory session grants are not suitable for production restart behavior.

## Follow-ups

- Persistent encrypted identity store.
- Controller CA or trust-on-first-use mode.
- mTLS between controller and node agent.
- Node heartbeat signing.
- Secure enrollment API.
