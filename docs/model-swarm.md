# CyberHIVE Model Swarm v0.1

## Scope

The first vertical slice proves that an artifact can be split into independently verified content-addressed chunks, distributed across multiple peers, downloaded concurrently, cached locally, and reassembled with whole-artifact verification.

## Data plane

1. `pack` reads an artifact and creates fixed-size chunks.
2. Every chunk is addressed by SHA-256 and stored in the local CAS.
3. A manifest records ordered chunk metadata and the whole-artifact SHA-256.
4. `inventory` creates an explicit development peer inventory for the artifact. This is a discovery contract, not a transport contract.
5. `serve` exposes CAS chunks through the development HTTP transport.
6. `fetch` loads and strictly validates the manifest and peer inventory, skips only locally verified chunks, downloads missing or corrupt chunks from peers, and can use an explicitly configured origin as the final fallback.
7. The artifact is assembled into a temporary file and committed only after all chunks are verified, the final SHA-256 matches the manifest, and the request has not been cancelled.

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

## Reliability v0.1

- Resume is CAS-based: a chunk is skipped only when its stored bytes re-hash to the expected SHA-256.
- A corrupt local CAS object is treated as missing and may be atomically replaced by verified bytes.
- Peer attempts are bounded. The default is one pass over candidate peers; callers may configure additional rounds, with the starting peer rotated between rounds.
- Chunk bytes are size- and SHA-256-verified before they are committed to CAS, so a corrupt peer cannot poison the cache.
- Origin fallback is optional and explicit. It is attempted only after peer attempts fail; omitting it preserves fully offline operation.
- Cancellation is checked during download and assembly. Temporary assembly files are removed and the final output path is not committed after cancellation.

CLI origin fallback uses the same development chunk HTTP contract:

```sh
cyberhive fetch <manifest> <peers.json> <cas-dir> <output> [origin-url]
```

The origin URL is not auto-discovered and does not enable Internet access by itself.

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
