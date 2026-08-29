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


## Verified session identity in receipts

Gateway receipts include the authenticated `session_id` from the verified signed envelope. Downstream projection layers must prefer this gateway-owned session identity over sender-controlled payload fields. This prevents a valid node session from mutating tasks that were dispatched to another active session of the same node.


## Receipt identity source

Receipt identity is derived from the envelope being verified, not by rediscovering an envelope with the same ID in gateway inbox/outbox history. This preserves the verified inbound direction, purpose and session even if a caller-controlled envelope ID collides with an existing outbound envelope.
