# CyberHIVE

CyberHIVE is an open-source, local-first AI fabric that turns compute, storage, networks and IoT into one secure, self-organizing peer-to-peer intelligence layer.

## Model Swarm v0.1

The first implementation slice adds a content-addressed model distribution core:

- fixed-size model chunks;
- SHA-256 integrity verification;
- local content-addressed storage (CAS);
- peer chunk inventory;
- concurrent multi-peer retrieval;
- peer failover per chunk;
- whole-artifact verification;
- HTTP peer transport behind an interface.

The coordinator is control plane only: model bytes do not need to transit through it.

### Quick start

```sh
go test ./...
go build ./cmd/cyberhive
./cyberhive pack ./model.gguf ./data/cas > model.manifest.json
./cyberhive serve ./data/cas 127.0.0.1:8787
```

`serve` currently has no authentication and therefore binds only where the operator explicitly tells it to. Do not expose this development transport to an untrusted network.

See [`docs/model-swarm.md`](docs/model-swarm.md) and [`docs/adr/0001-model-swarm.md`](docs/adr/0001-model-swarm.md).

## Status

Early development. Interfaces and manifest schemas may change before the first stable release.
