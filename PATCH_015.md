# Patch 015 — Node Heartbeat & Capability Sync MVP

Adds authenticated heartbeat ingestion, capability snapshots, liveness evaluation and scheduler sync.

## Added

- `src/cyberhive_core/node_heartbeat.py`
- `schemas/node-heartbeat.schema.json`
- `scripts/validate_node_heartbeat_mvp.py`
- `scripts/demo_node_heartbeat.py`
- `tests/test_node_heartbeat_mvp.py`
- `docs/NODE_HEARTBEAT_MVP.md`
- `docs/adr/ADR-0017-node-heartbeat-capability-sync-mvp.md`

## Security posture

If identity registry integration is enabled, heartbeats require:

- known node identity,
- enrolled trust state,
- active session id,
- valid session token.

No network listener, shell execution, remote execution or physical side effect is introduced.
