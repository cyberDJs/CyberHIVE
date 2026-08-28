# ADR-0005: Inventory and Exposure Gateway MVP

## Status

Accepted

## Context

CyberHIVE must safely manage resources such as cameras, local services,
documents, model runtimes, sensors and worker nodes. Some resources may be
indexable, some must remain opaque, and some may be temporarily exposed to
external users.

A single resource status is insufficient. "Allowed" does not describe whether a
resource may be indexed, used by agents, exposed on LAN, or published publicly.

## Decision

CyberHIVE Inventory uses independent axes:

- enabled / disabled
- indexed / non-indexed
- allowed / gated / denied
- private / lan / authenticated / public
- public / internal / sensitive / secret

CyberHIVE Exposure Gateway is the only approved path for publishing private or
local resources. It creates scoped, expiring grants and blocks direct device
access by default.

## Consequences

Positive:

- clearer security posture,
- safer device publishing,
- reusable capability model,
- better foundation for UI, policy and agent routing.

Negative:

- more metadata must be maintained,
- public exposure requires explicit configuration,
- authentication and policy integration are still required after MVP.

## Security invariant

Direct exposure of private devices is not allowed. Gateway-mediated,
authenticated and auditable exposure is required.
