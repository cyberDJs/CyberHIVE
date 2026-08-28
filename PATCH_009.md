# Patch 009 — Integration Orchestrator MVP

## Purpose

Patch 009 connects the MVP modules into one explainable orchestration plan.

Before this patch, CyberHIVE could independently decide reuse, data placement,
forecasting hints, routing and prewarm actions. This patch adds a small
coordination layer that decides the order of those decisions and records why each
step happened.

## Added

- `IntegrationOrchestrator`
- `OrchestrationRequest`
- `OrchestrationPlan`
- `OrchestrationStep`
- `OrchestrationAction`
- orchestration plan JSON schema
- validation script
- demo script
- unit tests
- ADR `ADR-0011-integration-orchestrator-mvp.md`

## Behavior

The MVP orchestration order is:

1. Check exact cache/reuse.
2. If reusable, skip compute execution.
3. Evaluate requested data placement.
4. Create data migration candidates from Data Fabric.
5. Normalize forecast scheduler hints for the router.
6. Route the workload.
7. Generate prewarm plans.
8. Return one auditable plan.

The orchestrator still does not execute workloads or move data. It produces a
safe plan that can later be handed to an executor.

## Validation

```bash
PYTHONPATH=src python3 scripts/validate_integration_orchestrator_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_integration_orchestrator.py
```
