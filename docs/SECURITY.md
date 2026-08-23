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

## Never do by default

- expose inference/admin APIs directly to the public Internet
- run workloads privileged without a documented need
- mount the host Docker socket into application containers
- accept arbitrary remote code as a normal model/skill payload
- silently auto-update critical components without health gates
