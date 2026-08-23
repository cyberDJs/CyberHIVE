# Architecture

## M0 baseline

CyberHIVE starts as a modular monolith plus isolated model runtimes. The controller owns configuration, identity, scheduling metadata, audit and the web/API control plane. Workers expose narrowly scoped capabilities and run inference workloads behind authenticated interfaces.

## Logical components

1. **Control API** — authenticated control-plane API.
2. **Web Console** — browser/kiosk administration.
3. **Node Registry** — identities, capabilities, heartbeats and lifecycle.
4. **Model Registry** — model metadata, compatibility and deployment state.
5. **Scheduler** — chooses eligible worker/runtime based on capacity and constraints.
6. **Runtime Adapter Layer** — replaceable adapters for inference backends.
7. **Audit/Event Log** — security-relevant and operational events.
8. **Update/Recovery Manager** — staged updates, health gates and rollback.

## Initial deployment topology

A single machine may host controller + worker. Multi-node operation must not be required for MVP. Remote workers are an extension of the same identity and API contracts, not a separate product.

## Security boundary

No worker is trusted merely because it is on the LAN. Enrollment creates identity. Control traffic is authenticated; secrets are not stored in repository configuration. Public exposure is opt-in.

## Performance rule

Every layer added between user request and model runtime must justify measurable latency, reliability or security value.
