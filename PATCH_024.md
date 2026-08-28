# Patch 024 — Codex P1 Security Repair

Status: candidate

This patch addresses the Codex P1 review findings raised against PR #21.

## Fixes

- Expire approved approval grants when consumed after TTL.
- Bind resumed approvals to the approved plan/request/subject.
- Invalidate issued node sessions when an identity is revoked or quarantined.
- Reject cross-node node-result reconciliation attempts.
- Reject ACKs whose authenticated node does not match the delivery owner.
- Restore the original target when an overwrite data move fails after backup creation.

## Verification

- `python3 -m unittest discover -s tests`
- `scripts/validate_node_reconciliation_mvp.py`
- `scripts/validate_worker_runtime_block_a.py`
- `scripts/demo_worker_runtime_block_a.py`
