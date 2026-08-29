# Codex P1 Repair Notes

This document records the security/correctness repair pass for Codex P1 findings on PR #21.

## Approval workflow

Approved grants remain short lived. Approval consumption now re-checks expiry, and resumed execution must match the original approval's plan ID, request ID, and subject.

## Node identity

Revoking or quarantining a node invalidates the node's outstanding sessions. Session verification also checks that the associated identity is still enrolled and matches the grant identity.

## Node delivery and reconciliation

Authenticated ACKs and node results must match the node that owns the delivery/task. A receipt from another node can no longer mutate a different node's delivery state.

## Data mover

Overwrite execution restores the original target from its backup when a failure occurs after backup creation, including final checksum failure cases.
