# CyberHIVE Model Swarm v0.1

## Scope

The first vertical slice proves that an artifact can be split into independently verified content-addressed chunks, distributed across multiple peers, downloaded concurrently, cached locally, and reassembled with whole-artifact verification.

## Data plane

1. `pack` reads an artifact and creates fixed-size chunks.
2. Every chunk is addressed by SHA-256 and stored in the local CAS.
3. A manifest records ordered chunk metadata and the whole-artifact SHA-256.
4. `inventory` creates an explicit development peer inventory for the artifact. This is a discovery contract, not a transport contract.
5. `serve` exposes CAS chunks through the development HTTP transport.
6. `fetch` loads and strictly validates the manifest and peer inventory, downloads missing chunks concurrently, verifies each hash, writes it to CAS, and tries another candidate peer on failure.
7. The artifact is assembled only after all chunks are available and the final SHA-256 matches the manifest.

The fetcher depends on a peer `Source` interface and a chunk `Client` interface. The initial explicit JSON inventory and HTTP transport can therefore be replaced independently by coordinator discovery, Dragonfly, QUIC, libp2p, or another approved backend without changing artifact identity.

## Explicit peer inventory

Development inventory is JSON and intentionally boring:

```json
{
  "peers": [
    {
      "id": "peer-a",
      "base_url": "http://127.0.0.1:8787",
      "chunks": ["<sha256>"]
    }
  ]
}
```

Unknown JSON fields, duplicate peer IDs, unsupported URL schemes, and malformed hashes fail closed.

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

## Security gate

The current HTTP transport is not a trusted-network release. Hash verification provides content integrity only. Before real LAN exposure, CyberHIVE requires node enrollment and identity, authenticated encrypted sessions, artifact authorization, rate limits, and explicit exposure policy.
