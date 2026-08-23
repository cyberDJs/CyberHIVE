# ADR-0004: Content-addressed peer-to-peer model distribution

- Status: Proposed
- Date: 2026-08-23
- Decision owners: CyberHIVE maintainers

## Context

CyberHIVE is local-first and must remain useful offline and on a single node. AI model artifacts are large enough that repeatedly downloading the same bytes from an Internet origin or a central coordinator wastes bandwidth, time, and infrastructure. LAN reachability is not sufficient identity, and public exposure must remain opt-in.

## Decision

CyberHIVE model artifacts use content-addressed chunks. Version 0.1 uses fixed-size chunks and SHA-256 from the Go standard library. A manifest binds chunk order, size, per-chunk SHA-256, and whole-artifact SHA-256.

Peers may exchange verified chunks directly. The coordinator may provide peer discovery and scheduling, but model bytes must not require transit through the coordinator. A node stores verified downloaded chunks in its local CAS immediately, making them available for later seeding subject to authorization policy.

Peer transport and peer discovery remain behind separate interfaces so a future Dragonfly, QUIC, libp2p, coordinator-backed discovery source, or native CyberHIVE backend can replace the initial explicit inventory and HTTP transport without changing artifact identity.

## Consequences

Positive:
- local and offline swarms remain functional;
- origin traffic decreases as the swarm gains copies;
- chunks are independently verifiable and resumable;
- a coordinator cannot become the model-data bottleneck;
- discovery and transport can evolve independently;
- the first implementation has no third-party Go runtime dependencies.

Negative:
- v0.1 fixed-size chunking does not deduplicate shifted content as efficiently as content-defined chunking;
- HTTP transport does not yet provide node identity or encryption by itself;
- explicit JSON inventory is operationally manual and is only a bootstrap discovery implementation;
- peer scheduling initially uses explicit inventory rather than measured topology and throughput.

## Security boundary

Untrusted peers may provide bytes, but bytes are accepted only after cryptographic hash verification. Hash verification provides integrity, not authorization. Production peer discovery and serving must require an authenticated node identity and explicit artifact authorization before private artifacts are exposed.

Internet-facing seeding, automatic port mapping, anonymous DHT discovery, and public swarm participation are out of scope for v0.1 and disabled by design.

## Rejected alternatives

- Central coordinator proxy for model bytes: rejected because it creates a bandwidth bottleneck and unnecessary data hop.
- BitTorrent protocol as the mandatory core: rejected because it couples CyberHIVE artifact identity to a specific transport and public-swarm assumptions.
- Kubernetes/Redis/NATS for v0.1: rejected because no measured requirement justifies the operational cost.
- Content-defined chunking in the first vertical slice: deferred until fixed-size behavior and cache hit metrics exist.

## Migration and rollback

The manifest is explicitly versioned. Future chunking algorithms must use a new schema/version or algorithm field while retaining readers for supported older manifests.

The explicit peer inventory is non-canonical runtime input and can be replaced without artifact migration. Rollback is removal of the feature branch/build. No canonical data migration or production state is required for v0.1.
