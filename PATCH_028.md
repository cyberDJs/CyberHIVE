# PATCH_028 — Block I P1 Session ACK and Alias Quarantine Repair

## Scope

Repairs Codex Block I re-review findings for PR #21 after PATCH_027.

## Changes

- `NodeDeliveryService.record_gateway_receipt()` now passes verified `GatewayReceipt.session_id` to `ReliableDeliveryQueue.mark_acked()`.
- `NodeResultReconciler` now quarantines every payload alias when a supplied known alias fails node/session ownership.
- `SecureNodeGateway` now builds receipt direction/purpose/session from the envelope being verified instead of reverse-searching inbox/outbox by envelope ID.
- Added regression tests for:
  - same-node wrong-session ACK rejection,
  - wrong-session alias quarantine for `action_request_id`,
  - receipt identity with inbound/outbound envelope ID collision.
- Updated delivery, reconciliation and gateway docs.

## Safety boundary

No shell execution, remote execution, network transport, deployment, persistence migration, privileged execution, secret exposure or production mutation.

## Verification

```text
Ran 159 tests
OK
OK: Node Result Reconciliation MVP validation passed
OK: Secure Node Gateway MVP validation passed
OK: Worker Runtime Block A validation passed
worker demo: summary: succeeded total=1 succeeded=1 failed=0
node reconciliation demo: summary: status=failed total=2 succeeded=1 failed=1 pending=0
```
