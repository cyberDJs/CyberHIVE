# Patch 017 — Secure Channel MVP

Adds signed message envelopes for CyberHIVE node/controller communication.

## Adds

- `SecureChannel`
- `SignedChannelEnvelope`
- `ReplayGuard`
- `SecureChannelRouter`
- `ChannelVerification`
- schema `secure-channel-envelope.schema.json`
- docs `NODE_SECURE_CHANNEL_MVP.md`
- ADR `ADR-0019-secure-channel-mvp.md`
- validation, demo and tests

## Guarantees

- HMAC signatures over canonical envelopes.
- Session verification against `NodeIdentityRegistry`.
- Direction and purpose checks.
- Timestamp freshness and expiry checks.
- Monotonic sequence / replay guard.
- No sockets, no TLS stack, no shell, no SSH, no remote execution.

## Non-goals

- mTLS / PKI.
- Wire encryption.
- UDP/TCP transport.
- Real network service.
- Remote shell command execution.
