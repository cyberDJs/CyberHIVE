# ADR-0013: Add Policy & Governance MVP

## Status

Accepted

## Context

CyberHIVE now has orchestration and execution layers. Before enabling real side
effects, the system needs a deterministic policy layer that can explain whether
an action is allowed, requires approval or must be denied.

Without this layer, execution policy would remain scattered across individual
components.

## Decision

Add `PolicyGuard` as an explicit evaluation layer. It produces auditable
`PolicyDecision` objects for orchestration plans and exposure requests.

The initial implementation is local and dependency-free. It uses approval token
strings rather than external identity infrastructure.

## Consequences

Positive:

- side effects get a consistent approval vocabulary,
- dry-run remains first-class,
- rejected routes and sensitive exposure are blocked centrally,
- policy decisions can be journaled and audited.

Negative:

- policy remains static in the MVP,
- approvals are not cryptographically signed yet,
- there is not yet a full RBAC model.

## Follow-up

Future patches may add:

- signed approvals,
- role and tenant policy registry,
- policy-as-code files,
- integration with identity,
- execution engine enforcement hook.
