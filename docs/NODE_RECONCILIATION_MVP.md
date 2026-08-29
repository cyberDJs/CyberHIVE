# CyberHIVE Node Result Reconciliation MVP

Patch 020 adds the controller-side reconciliation layer between reliable node delivery, secure gateway receipts and execution-visible task state.

## Problem

Patch 019 can say whether a node message was queued, dispatched, ACKed, retried, expired or dead-lettered. That is necessary, but not sufficient:

- ACK means the node received a message, not that the action finished.
- Action results arrive later and need correlation.
- Error envelopes need to become execution-visible failure state.
- Unknown results must not silently mutate known runs.
- Execution/run summaries need a projection of node task state.

## MVP decision

Add `NodeResultReconciler` as a pure in-memory reconciliation boundary.

It consumes:

- `DeliveryItem` from `ReliableDeliveryQueue`,
- verified `GatewayReceipt` objects from `SecureNodeGateway`,
- ACK, ACTION_RESULT and ERROR payloads.

It produces:

- `NodeTaskRecord`,
- append-only `NodeTaskEvent` history,
- optional JSONL `ReconciliationJournal`,
- `RunReconciliationSummary` for execution-run or plan keys.

## Lifecycle

```text
DeliveryItem
  -> NodeTaskRecord registered
  -> ACK receipt reconciled
  -> ACTION_RESULT / ERROR receipt reconciled
  -> per-run summary projected
```

## Status model

- `registered`
- `queued`
- `dispatched`
- `retry_wait`
- `acked`
- `succeeded`
- `failed`
- `expired`
- `dead_letter`
- `cancelled`
- `orphaned`
- `ignored`

## Correlation keys

The reconciler accepts multiple correlation keys because node transports and agent implementations may report different identifiers:

- `delivery_id`
- `correlation_id`
- `ack_for`
- `envelope_id`
- `request_id`
- `action_request_id`

Unknown results become `orphaned` records instead of being attached to an arbitrary run.

## Security posture

The reconciler does not verify signatures directly. It intentionally depends on `SecureNodeGateway` and `SecureChannel` to produce already-verified receipts.

A receipt is ignored unless:

- status is `recorded`,
- direction is `node_to_controller`,
- purpose is one of `ack`, `action_result`, `error`.

This keeps reconciliation boring: it projects trusted gateway facts; it does not become a second network security implementation.

## Non-goals

This MVP does not:

- open sockets,
- execute node actions,
- mutate execution runs directly,
- invent success from ACK,
- treat orphaned results as successful,
- persist secrets.

## Next step

The next patch should wire this into execution/control-plane orchestration so delivery, result reconciliation and execution run state are shown as a single controller view.


## Session-bound reconciliation

When a registered delivery has a `session_id`, reconciliation requires the verified gateway receipt session to match that delivery session. Payload-provided `session_id` is treated only as a consistency claim; it cannot substitute for the authenticated session retained by `GatewayReceipt`. Mismatched or missing verified sessions become orphaned records and do not mutate the owner task.

The alias index also preserves learned `action_request_id` values from result/error payloads so later terminal updates can correlate through the same action request alias.


## Alias quarantine on ownership/session mismatch

When any supplied payload alias resolves to an existing task but fails node or verified-session matching, the reconciler treats the whole payload alias set as untrusted for the resulting orphan. Companion aliases such as `action_request_id` are not learned from mismatched receipts. The owner session can still reconcile the original delivery later by presenting a valid alias under the verified session.

## Envelope-candidate mismatch quarantine

Alias quarantine also applies when the known mismatched candidate comes from gateway-owned receipt identity, including `receipt.envelope_id`, not only when the mismatched value was supplied in the payload. Any known-candidate node/session mismatch causes the complete payload alias set to be excluded from orphan indexing, so unknown companion aliases cannot be learned through envelope identity collisions.

