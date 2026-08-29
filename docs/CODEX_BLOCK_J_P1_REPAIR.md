# Codex Block J P1 Repair

## Problem

Codex re-review of PATCH_028 on PR #21 reported two fresh P1 issues:

1. ACK receipts with `GatewayReceipt.session_id=None` could still complete a same-node delivery because `ReliableDeliveryQueue.mark_acked()` treated `None` as a skipped session check.
2. Node result reconciliation quarantined all payload aliases only when the mismatched candidate was itself a payload alias. A known mismatch discovered through gateway-owned `receipt.envelope_id` could still let a wrong-session orphan learn a companion alias such as `action_request_id`.

## Decision

PATCH_029 keeps the existing in-memory MVP boundaries and tightens identity checks at the two affected projection layers:

- ACK completion now requires a non-null verified session before `ACKED` can be recorded.
- Any known-candidate ownership/session mismatch, including one found through receipt envelope identity, quarantines the full payload alias set before orphan indexing.

## Security impact

The repair closes two remaining same-node multi-session poisoning paths:

- A manually constructed or malformed recorded ACK receipt cannot use a null session as a wildcard.
- A wrong-session result cannot use an envelope-ID collision to teach an orphan a new action-request alias.

No network transport, shell execution, remote execution, persistence migration, secret handling, deployment or production mutation is introduced.

## Compatibility impact

`ReliableDeliveryQueue.mark_acked()` now requires callers to provide an authenticated session id. Existing secure gateway paths already supply `GatewayReceipt.session_id`; direct test or integration callers must do the same.

## Rollback

Revert PATCH_029 files to the PATCH_028 versions:

- `src/cyberhive_core/node_delivery.py`
- `src/cyberhive_core/node_reconciliation.py`
- `tests/test_node_delivery_mvp.py`
- `tests/test_node_reconciliation_mvp.py`
- related docs

## Verification

```text
PYTHONPATH=src python3 -m unittest discover -s tests
Ran 161 tests
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
