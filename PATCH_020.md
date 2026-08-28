# Patch 020 — Node Result Reconciliation MVP

## Adds

- `src/cyberhive_core/node_reconciliation.py`
- `tests/test_node_reconciliation_mvp.py`
- `scripts/validate_node_reconciliation_mvp.py`
- `scripts/demo_node_reconciliation.py`
- `schemas/node-reconciliation-record.schema.json`
- `docs/NODE_RECONCILIATION_MVP.md`
- `docs/adr/ADR-0022-node-result-reconciliation-mvp.md`
- `INSTALL_PATCH_020.md`

## Purpose

Turns reliable delivery state and secure gateway receipts into execution-visible node task state.

The key distinction:

```text
ACK = node received message
ACTION_RESULT = node finished or refused the action
ERROR = node/gateway reported failure
```

## Safety

This patch does not execute remote actions. It only reconciles already-verified gateway facts.
