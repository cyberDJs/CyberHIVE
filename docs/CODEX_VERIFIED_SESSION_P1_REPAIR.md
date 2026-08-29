# Codex Verified Session P1 Repair

## Problem

Codex re-review found that reconciliation was still bound only to node identity plus sender-controlled payload aliases. A node with multiple active sessions could submit a verified receipt from session A that referenced a delivery registered to session B and omit `session_id` from the payload. Because `GatewayReceipt` did not retain the verified envelope session, `NodeResultReconciler` could not compare the authenticated session with the registered task session.

## Fix

Patch 027 makes the gateway receipt carry the verified envelope `session_id` and makes reconciliation fail closed for session-scoped deliveries unless that verified receipt session matches the registered `NodeTaskRecord.session_id`.

The patch also preserves `action_request_id` aliases learned from result/error payloads, addressing the low-risk P2 raised in the same re-review area.

## Security effect

- Same-node cross-session receipts become orphaned instead of mutating another session's task.
- Sender-controlled payload `session_id` cannot override the verified gateway session.
- Receipts with mismatched payload and verified session are rejected for known records.
- Owner sessions can still reconcile their original deliveries after forged/mismatched receipts.

## Changed files

- `src/cyberhive_core/secure_node_gateway.py`
- `src/cyberhive_core/node_reconciliation.py`
- `schemas/secure-node-gateway-receipt.schema.json`
- `tests/test_secure_node_gateway_mvp.py`
- `tests/test_node_reconciliation_mvp.py`
- `scripts/validate_node_reconciliation_mvp.py`
- `scripts/demo_node_reconciliation.py`

## Verification

```text
PYTHONPATH=src python3 -m unittest discover -s tests
Ran 156 tests
OK

PYTHONPATH=src python3 scripts/validate_node_reconciliation_mvp.py
OK: Node Result Reconciliation MVP validation passed

PYTHONPATH=src python3 scripts/validate_secure_node_gateway_mvp.py
OK: Secure Node Gateway MVP validation passed

PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
OK: Worker Runtime Block A validation passed

PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
summary: succeeded total=1 succeeded=1 failed=0
```

`python3 scripts/validate_schemas.py` was also probed and still reports pre-existing missing `$id` fields in three Block A schemas. This patch does not change those schemas.

## Rollback

Revert Patch 027 files to PATCH_026 state. Rollback removes session-bound reconciliation, so it should only be used if a compatibility issue is more urgent than the verified-session security boundary.
