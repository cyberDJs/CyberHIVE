# ADR-0015: Node Agent & Action Dispatch MVP

## Status

Accepted

## Context

CyberHIVE can now plan, route, forecast, evaluate policy, request approval and
create execution runs. It still needs a safe boundary for node-local actions.

## Decision

Introduce a local, typed `NodeAgent` interface and `NodeActionDispatcher`.

The MVP supports only structured actions and local deterministic handlers. It
does not run arbitrary commands or remote execution.

## Consequences

Positive:

- side effects are represented as typed requests/results,
- dry-run remains first-class,
- node-side policy checks are redundant and auditable,
- future real executors can attach behind a narrow interface.

Negative:

- real model prewarm and file moves are still not executed,
- the node agent is in-memory only,
- no node enrollment or network transport yet.
