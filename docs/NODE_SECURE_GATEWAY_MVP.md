# CyberHIVE Secure Node Gateway MVP

Patch 018 puts a narrow integration boundary above signed secure-channel envelopes.

```text
NodeIdentityRegistry + sessions
        ↓
SessionCredentialVault
        ↓
SecureNodeGateway
        ↓
SecureChannel verification
        ↓
HeartbeatStore / NodeActionDispatcher / receipts
```

## Responsibilities

- Keep node session tokens out of ordinary caller paths.
- Build signed controller-to-node action envelopes.
- Receive signed node-to-controller messages.
- Verify signature, session, direction, purpose, freshness, and replay.
- Dispatch heartbeats to `NodeHeartbeatStore`.
- Dispatch controller actions to `NodeActionDispatcher` when running local MVP simulations.
- Record action results, ACKs, and errors.

## Security posture

The gateway does **not** implement network I/O, TLS, long-term secret storage, remote execution, SSH, shell commands, or Docker operations.

Secrets are in-memory only in this MVP. A later patch should replace `SessionCredentialVault` with a keychain / sealed local store / KMS-backed adapter.

## Message handling

| Direction | Purpose | Action |
|---|---|---|
| node → controller | heartbeat | verify and ingest heartbeat |
| controller → node | action | verify and dispatch to local node-agent boundary |
| node → controller | action_result | verify and record result |
| either | ack | verify and record ACK |
| either | error | verify and record error |

Unsupported direction/purpose combinations are denied.
