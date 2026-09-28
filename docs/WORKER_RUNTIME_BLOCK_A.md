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

## Block L hardening

Post-merge hardening tightens worker runtime failure boundaries without adding
shell, Docker, SSH, privileged execution, deployment, or production access.

Additional guarantees:

1. Unsupported or malformed action names are parsed before ACK generation. A
   parse failure returns a signed denied `ACTION_RESULT` and does not emit an ACK,
   so the controller does not stop retries for an action the worker never
   accepted.
2. Local resource requests now preserve action-specific defaults before applying
   explicit payload overrides. For example, `prewarm_model` keeps its default
   VRAM and memory budget unless the payload intentionally overrides them.
3. `WorkerRuntimePolicy.max_result_payload_bytes` is enforced before signing the
   result envelope. Oversized handler metadata/events are replaced with a bounded
   failure payload that records truncation metadata.
