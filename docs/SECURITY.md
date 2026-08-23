# Security

## Baseline

- least privilege
- authenticated control plane
- explicit node enrollment
- secrets outside Git
- auditable administrative actions
- local-only listening defaults where practical
- TLS for remote control traffic
- dependency and container image pinning
- signed/reproducible release direction
- staged upgrades with rollback

## Model Swarm

- LAN reachability is never peer identity.
- Development HTTP serving is loopback-only.
- LAN Model Swarm traffic uses TLS 1.3 mutual authentication.
- The v0.1 offline trust root is a local CyberHIVE CA; node identity is carried in a SPIFFE-compatible certificate URI SAN.
- Node private keys are stored outside Git with mode `0600` and are not automatically overwritten.
- Authentication does not imply authorization: artifact policy binds allowed node IDs to an artifact SHA-256 and its chunk set.
- Unregistered artifacts and unauthorized peers fail closed.
- Per-peer concurrency and request-rate limits protect the serving node from accidental or hostile exhaustion.
- Operator registration into local policy is the v0.1 authority gate for manifests; remote/public catalogs require signed manifests or another trusted registry mechanism before federation.

See `docs/adr/ADR-0005-model-swarm-peer-security.md`.

## Never do by default

- expose inference/admin APIs directly to the public Internet
- run workloads privileged without a documented need
- mount the host Docker socket into application containers
- accept arbitrary remote code as a normal model/skill payload
- silently auto-update critical components without health gates
- expose the unauthenticated Model Swarm development server beyond loopback
- treat discovery of a peer as enrollment or authorization
