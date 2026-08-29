# CyberHIVE Worker Runtime Block A MVP

Block A turns the node side from passive receipt tracking into a deterministic local runtime loop.

## Added components

- Patch 021: Node Worker Runtime Loop MVP
- Patch 022: Action Handler Registry MVP
- Patch 023: Local Resource Guard MVP

## Runtime flow

```text
reliable delivery item
→ signed controller ACTION envelope
→ NodeWorkerRuntime
→ secure channel verification
→ node ACK envelope
→ LocalResourceGuard
→ ActionHandlerRegistry
→ AgentActionResult
→ signed ACTION_RESULT envelope
→ SecureNodeGateway
→ NodeResultReconciler
```

## Safety boundary

This block still does not execute shell commands, Docker, SSH, privileged operations, real file moves, deployments, or production changes.

The worker runtime handles only typed actions already allowed by the node action boundary. The resource guard is an in-memory preflight/reservation model; it is not an OS-level cgroup or sandbox.

## Why this matters

Before this block, CyberHIVE could reliably send signed actions and reconcile results, but the node-local loop was missing. Now the control plane has a modeled node worker lifecycle with ACK/result separation and local resource checks.
