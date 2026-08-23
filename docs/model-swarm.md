# CyberHIVE Model Swarm v0.1

## Scope

The first vertical slice proves that an artifact can be split into independently verified content-addressed chunks, distributed across multiple peers, downloaded concurrently, cached locally, and reassembled with whole-artifact verification.

## Data plane

1. `pack` reads an artifact and creates fixed-size chunks.
2. Every chunk is addressed by SHA-256 and stored in the local CAS.
3. A manifest records ordered chunk metadata and the whole-artifact SHA-256.
4. Peer inventory maps chunk hashes to authenticated peer endpoints. Authentication is a required next security layer; v0.1 tests use trusted in-process peers only.
5. The fetcher downloads missing chunks concurrently, verifies each hash, writes it to CAS, and tries another candidate peer on failure.
6. The artifact is assembled only after all chunks are available and the final SHA-256 matches the manifest.

## Explicit non-goals for v0.1

- public DHT;
- NAT traversal or UPnP;
- anonymous peers;
- Internet seeding by default;
- semantic model registry;
- content-defined chunking;
- erasure coding;
- coordinator HA;
- Kubernetes.

## Next security milestone

Introduce node enrollment, authenticated peer sessions, authorization for artifact/chunk serving, rate limits, and transport encryption before enabling a real LAN swarm outside controlled development tests.
