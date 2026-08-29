# Approval Workflow MVP

Patch 012 adds the missing bridge between policy decisions and execution.

## Flow

```text
OrchestrationPlan
  -> PolicyGuard
  -> PolicyDecision
  -> ApprovalBroker, when approval is required
  -> approved PolicyContext
  -> GovernedExecutionController
  -> ExecutionEngine
```

## Why this exists

Patch 011 introduced approval tokens, but tokens alone are not an operational workflow. This patch gives CyberHIVE a local, auditable approval broker so a dangerous plan can pause, explain what is needed, receive scoped approval, and then re-check policy before execution.

## MVP limits

- Local in-memory broker.
- Optional JSONL journal.
- No Slack, email or web UI integration yet.
- No long-lived grants.
- No remote execution.

## Approval tokens

The broker handles the tokens defined in Policy & Governance, such as:

- `execute.live`
- `data.move.execute`
- `runtime.prewarm.execute`
- `secret.process`
- `exposure.public`

## Governed execution

`GovernedExecutionController` evaluates policy before execution.

Possible outcomes:

- `dry_run`
- `executed`
- `approval_required`
- `denied`

If approvals are granted, the controller rebuilds the policy context and evaluates policy again. This prevents stale approval state from bypassing newer policy checks.
