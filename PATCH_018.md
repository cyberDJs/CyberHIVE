# Patch 018 — Secure Node Gateway MVP

Adds a secure gateway layer that owns in-memory session credentials, verifies signed envelopes, dispatches accepted heartbeats/actions to local MVP surfaces, and records ACK / error / action-result receipts.

## Added

- `SessionCredential`
- `SessionCredentialVault`
- `SecureNodeGateway`
- `GatewayReceipt`
- `GatewayMessageStatus`
- secure action envelope builder
- secure ACK envelope builder
- heartbeat ingress via `SecureChannelRouter`
- controller-to-node action dispatch via `SecureChannelRouter`
- node-to-controller action-result recording
- ACK / ERROR recording
- schema `secure-node-gateway-receipt.schema.json`
- docs and ADR

## Non-goals

- no sockets
- no TLS implementation
- no persistent secret storage
- no remote execution
- no shell / SSH / Docker invocation
- no production transport daemon
