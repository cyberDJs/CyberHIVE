# Patch 012 — Approval Workflow MVP

Adds human-in-the-loop approval workflow and governed execution.

## New components

- `ApprovalBroker`
- `ApprovalRequest`
- `ApprovalGrant`
- `ApprovalJournal`
- `GovernedExecutionController`
- `GovernedExecutionResult`

## Core behavior

- Turns `PolicyDecision(REQUIRE_APPROVAL)` into scoped approval requests.
- Tracks required, granted and missing approval tokens.
- Supports partial approval, full approval, denial, cancellation and expiry.
- Rebuilds `PolicyContext` from approved tokens.
- Wraps `ExecutionEngine` behind `PolicyGuard`.
- Enables execution-side allowances only when the relevant approval tokens exist.

## Safety invariants

- No approval request is created for `ALLOW`, `WARN` or `DENY` decisions.
- Approvals are scoped to one policy decision.
- Approval requests expire.
- Unknown or unnecessary tokens are rejected.
- Denied, expired, cancelled and approved requests are closed.
- Live execution still re-evaluates policy before running.
