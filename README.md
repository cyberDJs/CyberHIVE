# CyberHIVE AI

Open-source, local-first platform for operating, orchestrating and managing AI models, agents, tools, skills and compute nodes on owned hardware, servers and optional cloud infrastructure.

## Status

Architecture / bootstrap phase. Initial reference target: headless Linux host with NVIDIA RTX 3070, web administration and optional kiosk mode.

## Start here

1. Read `docs/PROJECT_CONTEXT.md`.
2. Read `AGENTS.md` before making code or infrastructure changes.
3. Use `docs/adr/` for architectural decisions.
4. Keep source design media in Google Drive and approved exports in `assets/`.
5. Keep reusable ChatGPT workflows in `skills/`.

## Model Swarm v0.1

Model Swarm adds a content-addressed peer-to-peer model distribution core:

- fixed-size SHA-256 chunks and local CAS;
- strict versioned manifests;
- explicit peer inventory behind a replaceable discovery interface;
- concurrent multi-peer retrieval with per-chunk failover;
- atomic reassembly and whole-artifact verification;
- development HTTP transport behind a replaceable client interface.

The coordinator remains control plane only; model bytes do not need to transit through it.

Local development workflow:

```sh
go build ./cmd/cyberhive
./cyberhive pack ./model.gguf ./data/source-cas > model.manifest.json
./cyberhive inventory peer-a http://127.0.0.1:8787 model.manifest.json > peers.json
./cyberhive serve ./data/source-cas 127.0.0.1:8787
./cyberhive fetch model.manifest.json peers.json ./data/destination-cas ./models/model.gguf
```

**Security status:** the HTTP peer transport is development-only. It has no node authentication or artifact authorization yet; do not expose it to an untrusted LAN or the Internet.

See [`docs/model-swarm.md`](docs/model-swarm.md) and [`docs/adr/ADR-0004-model-swarm.md`](docs/adr/ADR-0004-model-swarm.md).

## Repository map

- `cmd/` — Go command entry points
- `internal/` — internal Go implementation modules
- `docs/` — product, architecture, security, roadmap and runbooks
- `skills/` — reusable CyberHIVE ChatGPT skills
- `assets/` — approved repository-safe visual assets
- `src/` — application code
- `tests/` — automated tests
- `infra/` — deployment/IaC
- `scripts/` — project automation
