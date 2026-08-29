# Node Secure Channel MVP

Patch 017 adds a signed envelope layer between enrolled nodes and the CyberHIVE controller.

```text
Node Identity + Session
        ↓
SignedChannelEnvelope
        ↓
SecureChannel.verify()
        ↓
ReplayGuard
        ↓
Heartbeat / Action adapter
```

## Why

Discovery and enrollment prove that a node can join the fabric. Heartbeats and action dispatch still need a message-level safety boundary. This patch makes every controller/node message explicit, signed, directional, sequenced and replay-checked.

## What is signed

The signature covers canonical JSON containing:

- envelope id,
- node id,
- session id,
- direction,
- purpose,
- sequence,
- issued/expiry timestamps,
- correlation id,
- payload,
- metadata.

The signature uses HMAC-SHA256 with the session token returned by `NodeIdentityRegistry.issue_session()`.

## Direction and purpose

Supported directions:

- `node_to_controller`
- `controller_to_node`

Supported purposes:

- `heartbeat`
- `action`
- `action_result`
- `ack`
- `error`

Adapters can require an expected direction and purpose. A heartbeat cannot arrive as a controller-to-node action. Shocking, I know.

## Replay protection

`ReplayGuard` tracks the latest accepted sequence per:

```text
session_id + direction + purpose
```

It also records accepted message digests. Older or duplicated envelopes are rejected as replays.

## Security boundary

This MVP does not implement network transport or encryption. It is the message-authentication contract that future transports must preserve.

No sockets. No mTLS. No SSH. No shell. No remote execution.

## Later work

- mTLS transport.
- Per-node asymmetric signatures.
- Channel key rotation.
- Encrypted payload envelopes.
- Controller API endpoints.
- Stream framing over the Runtime Bus.
