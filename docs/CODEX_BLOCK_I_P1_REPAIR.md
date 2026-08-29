# Codex Block I P1 Repair

## Problem

Codex re-review of PR #21 after PATCH_027 found two fresh P1 issues:

1. Delivery ACK completion used the verified node identity but did not pass the verified gateway `session_id` into `ReliableDeliveryQueue.mark_acked()`. A node with multiple active sessions could ACK work dispatched to another session.
2. Wrong-session reconciliation quarantined only the known mismatched alias. A forged receipt could include a known victim `delivery_id` plus a new companion alias such as `action_request_id`, causing the orphan to learn that alias and poison later owner correlation.

Codex also reported a related P2: gateway receipt identity was rediscovered by envelope ID from inbox/outbox history instead of being taken directly from the envelope being verified.

## Decision

PATCH_028 keeps the repair minimal and local to the affected trust boundaries:

- pass `GatewayReceipt.session_id` into `ReliableDeliveryQueue.mark_acked()` from `NodeDeliveryService.record_gateway_receipt()`,
- quarantine every payload alias when any supplied known alias fails node/session ownership,
- build gateway receipts from the currently verified envelope identity instead of reverse-searching inbox/outbox by ID,
- add regression tests for same-node wrong-session ACKs, wrong-session alias poisoning, and envelope-ID collision receipt identity.

## Security impact

The controller no longer treats same-node active sessions as interchangeable for delivery ACKs or result reconciliation. Payload-supplied aliases remain useful for valid correlation, but a mismatched receipt cannot teach new aliases to the index.

## Compatibility

The public in-memory MVP APIs remain compatible. The change tightens validation. Previously accepted wrong-session ACK/result receipts now fail closed or become orphaned.

## Verification

Executed in a fresh reconstructed workspace:

```text
PYTHONPATH=src python3 -m unittest discover -s tests
Ran 159 tests
OK

PYTHONPATH=src python3 scripts/validate_node_reconciliation_mvp.py
OK: Node Result Reconciliation MVP validation passed

PYTHONPATH=src python3 scripts/validate_secure_node_gateway_mvp.py
OK: Secure Node Gateway MVP validation passed

PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
OK: Worker Runtime Block A validation passed

PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
summary: succeeded total=1 succeeded=1 failed=0

PYTHONPATH=src python3 scripts/demo_node_reconciliation.py
summary: status=failed total=2 succeeded=1 failed=1 pending=0
```

## Rollback

Revert PATCH_028 files to PATCH_027 state. No data migration or persistent state is introduced.
