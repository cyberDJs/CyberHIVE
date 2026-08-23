# CyberHIVE

CyberHIVE is an open-source, local-first AI fabric that turns compute, storage, networks and IoT into one secure, self-organizing peer-to-peer intelligence layer.

## Model Swarm v0.1

The first implementation slice adds a content-addressed model distribution core:

- fixed-size model chunks;
- SHA-256 integrity verification;
- local content-addressed storage (CAS);
- explicit peer inventory;
- concurrent multi-peer retrieval;
- peer failover per chunk;
- whole-artifact verification;
- HTTP peer transport behind an interface.

The coordinator is control plane only: model bytes do not need to transit through it.

### Local development workflow

On the source peer:

```sh
go build ./cmd/cyberhive
./cyberhive pack ./model.gguf ./data/source-cas > model.manifest.json
./cyberhive inventory peer-a http://127.0.0.1:8787 model.manifest.json > peers.json
./cyberhive serve ./data/source-cas 127.0.0.1:8787
```

Copy `model.manifest.json` and the explicit `peers.json` inventory to the destination peer, then run:

```sh
./cyberhive fetch model.manifest.json peers.json ./data/destination-cas ./models/model.gguf
```

`fetch` validates the manifest, downloads missing chunks concurrently, verifies every chunk before committing it to CAS, reassembles the artifact atomically, and verifies the final SHA-256.

> **Security status:** `serve` is development-only and has no peer authentication or artifact authorization yet. Bind it to localhost or a controlled test network only. Do not expose it to an untrusted LAN or the Internet.

See [`docs/model-swarm.md`](docs/model-swarm.md) and [`docs/adr/0001-model-swarm.md`](docs/adr/0001-model-swarm.md).

## Development gates

```sh
go vet ./...
go test -race ./...
go build ./cmd/cyberhive
```

## Status

Early development. Interfaces and manifest schemas may change before the first stable release.
