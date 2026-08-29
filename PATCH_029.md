# PATCH_029 — Block J P1 Null-Session ACK and Envelope Alias Quarantine Repair

## Scope

Repairs Codex Block J re-review findings for PR #21 after PATCH_028.

## Changes

- `ReliableDeliveryQueue.mark_acked()` now rejects ACK completion when the authenticated session id is missing.
- `NodeDeliveryService.record_gateway_receipt()` continues to pass the verified `GatewayReceipt.session_id`; null-session receipts now fail closed instead of acting as session wildcards.
- `NodeResultReconciler` now quarantines the full payload alias set for any known-candidate node/session mismatch, including candidates discovered through `receipt.envelope_id` or verification envelope identity.
- Added regression tests for:
  - recorded node-to-controller ACK receipt with `session_id=None`,
  - wrong-session envelope identity collision that tries to poison `action_request_id`.
- Updated delivery and reconciliation docs.

## Safety boundary

No shell execution, remote execution, network transport, deployment, persistence migration, privileged execution, secret exposure or production mutation.

## Verification

```text
Ran 161 tests
OK
OK: Node Result Reconciliation MVP validation passed
OK: Secure Node Gateway MVP validation passed
OK: Worker Runtime Block A validation passed
worker demo: summary: succeeded total=1 succeeded=1 failed=0
node reconciliation demo: summary: status=failed total=2 succeeded=1 failed=1 pending=0
```
