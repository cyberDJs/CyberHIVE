# Codex Re-review P1 Repair

## Context

After Block F was pushed, Codex re-reviewed PR #21 and reported two fresh P1 findings plus one cheap P2 hardening point.

## P1: Approval resume without required bindings

`ApprovalBroker.create_request` can be called directly without metadata. The repair makes `GovernedExecutionController.resume_with_approval` fail closed unless the approved request contains both:

- `metadata.plan_id` matching the plan being resumed
- `metadata.request_id` matching the orchestration request being resumed

This preserves the existing broker API while making governed execution refuse unbound approvals.

## P1: Cross-node alias poisoning

A forged/mismatched node receipt can mention another node's delivery ID. The previous repair made such receipts orphaned, but orphan indexing could still remap the known delivery alias to the orphan.

The repair tracks aliases observed during mismatched correlation as untrusted and prevents orphan indexing from overwriting existing alias ownership. A legitimate owner result can still reconcile the original task.

## P2: Outbound ACK receipts

`NodeDeliveryService.record_gateway_receipt` now ignores ACK receipts unless they are `NODE_TO_CONTROLLER`, preventing controller-produced/outbound ACK records from completing a delivery.

## Verification

Reconstructed workspace verification:

```text
Ran 153 tests in 1.032s
OK
OK: Node Result Reconciliation MVP validation passed
OK: Worker Runtime Block A validation passed
worker runtime demo: succeeded
```

## Remaining gate

After this patch is pushed, CI and Codex re-review must be checked again before any merge approval.
