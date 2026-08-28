# Node Delivery Queue MVP

Patch 019 adds a reliable controller-to-node delivery queue on top of the secure node gateway.

## Problem

Patch 018 can build signed action envelopes and record ACKs, but it does not track whether an outbound action has been acknowledged, retried, expired, or dead-lettered.

CyberHIVE needs an explicit reliability boundary before any real transport daemon exists.

## Decision

Add `node_delivery.py` with:

- `ReliableDeliveryQueue`
- `NodeDeliveryService`
- `DeliveryItem`
- `DeliveryPolicy`
- `DeliveryStatus`
- `DeliveryHistoryEvent`
- `DeliveryDispatchResult`

The queue is in-memory for MVP. It records lifecycle events and correlates ACK payloads back to delivery items by:

- `delivery_id`
- `correlation_id`
- `ack_for`
- `envelope_id`

## Lifecycle

```text
queued
  -> dispatched
  -> acked
```

Timeout path:

```text
queued
  -> dispatched
  -> retry_wait
  -> dispatched
  -> dead_letter | acked | expired
```

## Safety boundaries

This patch does not:

- open sockets,
- run a background worker,
- persist queue state,
- send packets on the network,
- execute shell commands,
- invoke SSH, Docker, systemd, or Kubernetes.

It only builds signed gateway envelopes and tracks delivery state.

## Why now

The secure node gateway is useful only if higher layers can tell whether an action was actually acknowledged. This patch creates the queue contract that a later transport layer can implement without changing orchestration, policy, or node identity code.

## Future work

- durable queue storage,
- transport adapter,
- rate limiting,
- per-node concurrency windows,
- poison-message quarantine,
- delivery metrics,
- queue draining on shutdown,
- operator UI for dead-letter handling.
