# PATCH 027 — Verified Session Reconciliation P1 Repair

## Summary

Fixes Codex P1: reconciliation must bind known deliveries to the verified gateway session, not to sender-controlled payload fields.

## Changes

- `GatewayReceipt` now carries `session_id` from the verified signed envelope.
- `GatewayReceipt.as_dict()` exposes `session_id`.
- `NodeResultReconciler` rejects known-record matches when the verified receipt session does not match the registered delivery session.
- Payload `session_id` is treated as an additional consistency claim, never as authority.
- Orphan records use the verified receipt session when available.
- Learned `action_request_id` aliases are indexed after result/error correlation.
- Validation/demo scripts now construct session-bound receipts.

## Tests

```text
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/validate_node_reconciliation_mvp.py
PYTHONPATH=src python3 scripts/validate_secure_node_gateway_mvp.py
PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
```

Observed result: 156 unit tests passed and all listed validation/demo commands passed.

## Safety boundary

No shell execution, SSH, Docker, deployment, production access, secret persistence, or privileged operation is introduced.
