# Policy & Governance MVP

Patch 011 introduces the first explicit governance layer for CyberHIVE.

The goal is not compliance theater. The goal is a small, auditable gate between
planning and side effects.

## Position in the architecture

```text
Integration Orchestrator
        ↓
Policy Guard
        ↓
Execution Engine
        ↓
Runtime Bus / Journal
```

The Policy Guard evaluates whether a plan or exposure request is:

- allowed,
- allowed with warnings,
- blocked until explicit approval,
- denied.

## Safety defaults

The MVP is intentionally conservative:

- dry-run is allowed by default,
- live execution requires approval,
- physical data movement requires approval,
- prewarm side effects require approval,
- rejected routes are denied unless explicitly overridden,
- secret resources cannot be exposed,
- public exposure requires explicit approval,
- recording and download require explicit approval.

## Approval tokens

The initial approval tokens are:

```text
execute.live
data.move.execute
runtime.prewarm.execute
secret.process
exposure.public
exposure.recording.enable
exposure.download.enable
route.reject.override
```

These are simple strings in the MVP. Later they can become signed approval
objects bound to identity, time, scope and request digest.

## Policy decision

A policy decision contains:

- outcome,
- subject,
- dry-run flag,
- findings,
- required approvals,
- metadata,
- timestamp.

The decision is serializable and can be stored in `GovernanceJournal` as JSONL.

## Non-goals

This patch does not add:

- RBAC database,
- OAuth/OIDC,
- remote policy server,
- signed approvals,
- distributed consensus,
- compliance pack templates.

Those can come later. The MVP adds the decision semantics first.
