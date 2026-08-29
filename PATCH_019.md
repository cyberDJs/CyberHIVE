# Patch 019 — Reliable Node Delivery Queue MVP

Adds reliable controller-to-node delivery tracking on top of Secure Node Gateway.

## Added

- `DeliveryPolicy`
- `DeliveryStatus`
- `DeliveryPriority`
- `DeliveryItem`
- `DeliveryHistoryEvent`
- `DeliveryDispatchResult`
- `ReliableDeliveryQueue`
- `NodeDeliveryService`
- ACK correlation by delivery id / correlation id / envelope id
- retry/backoff handling
- TTL expiry
- dead-letter handling
- schema `node-delivery-item.schema.json`
- docs and ADR

## Non-goals

- no sockets
- no background daemon
- no durable queue storage
- no real packet sending
- no remote execution
- no shell / SSH / Docker invocation
