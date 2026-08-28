# ADR-0011: Integration Orchestrator MVP

## Status

Accepted

## Context

CyberHIVE now has independent MVP modules for runtime frames, inventory,
exposure, data placement, safe data moving, cache/reuse, forecasting and routing.
Without a coordinator, higher-level workflows must manually call each module in
the correct order.

## Decision

Add `IntegrationOrchestrator` as a small local planner that composes these
modules into one auditable `OrchestrationPlan`.

The order is:

1. reuse check,
2. data placement,
3. data move candidate planning,
4. scheduler hint normalization,
5. compute routing,
6. prewarm planning.

## Consequences

Positive:

- one place to explain why a workload is reused, routed, queued or rejected,
- first real integration point across CyberHIVE Core,
- safer path toward an executor,
- testable and dependency-free.

Negative:

- the orchestrator currently reads router node state through a contained private
  accessor because the router MVP has no public node listing API yet,
- it is still a local in-memory coordinator,
- no durable workflow recovery exists yet.

## Follow-up

- add a public node-list accessor to `ComputeRouter`,
- add `Execution Planner MVP`,
- add durable plan log,
- connect plans to Runtime Bus operations.
