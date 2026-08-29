# Codex Alias Validation P1 Repair

## Finding

Codex re-review on PR #21 / commit `237d24685e` reported that node-result reconciliation accepted the first matching alias before validating all supplied aliases. A malicious node could submit a payload with its own valid `delivery_id` and a victim node's alias, causing alias-index poisoning.

## Repair

The reconciler now performs whole-payload alias validation before accepting a record. A receipt is accepted for a known task only if every supplied alias is either unknown or resolves consistently to that same task under the authenticated node/session boundary. Conflicting aliases force orphan handling.

## Expected effect

- Mixed valid/conflicting alias receipts do not mutate the matched task.
- Conflicting aliases are marked untrusted on the orphan record.
- `_index_record` skips untrusted aliases and preserves existing alias ownership.
- The legitimate owner can reconcile the original delivery after the forged receipt.

## Verification

Run:

```text
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/validate_node_reconciliation_mvp.py
PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
```
