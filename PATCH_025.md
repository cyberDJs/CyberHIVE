# PATCH 025 — Codex Re-review P1 Repair

## Scope

Repairs fresh Codex findings from the manual re-review on PR #21 head `6cb8d66`.

## Fixes

- Require explicit `plan_id` and `request_id` bindings before `resume_with_approval` can consume an approved request.
- Prevent mismatched cross-node receipts from poisoning reconciliation alias indexes.
- Reject controller-to-node ACK receipts in the delivery completion path.

## Regression tests

- Approval resume rejects approved requests missing plan/request binding metadata.
- Cross-node forged result cannot remap a known delivery alias away from the owning node.
- Outbound ACK gateway receipts do not complete deliveries.

## Safety boundary

No merge, deploy, production access, force-push, privileged execution, secret handling, shell execution, Docker, SSH, or host mutation is introduced.
