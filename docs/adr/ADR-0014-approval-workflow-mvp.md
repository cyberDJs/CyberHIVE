# ADR-0014: Approval Workflow MVP

## Status

Accepted

## Context

Policy & Governance can say that an operation requires approval, but the system needs a structured way to request, grant, deny and consume those approvals.

## Decision

Introduce a local Approval Workflow MVP:

- approval requests are scoped to one policy decision,
- approval tokens are explicit,
- partial approvals are supported,
- expired/denied/cancelled requests cannot be reused,
- governed execution re-evaluates policy before running.

## Consequences

CyberHIVE can now pause live execution until the required approval tokens exist. The workflow is still local and not integrated with Slack, web UI or external identity providers.
