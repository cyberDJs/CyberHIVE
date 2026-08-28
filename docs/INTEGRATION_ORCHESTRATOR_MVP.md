# CyberHIVE Integration Orchestrator MVP

## Decision

CyberHIVE needs a small orchestration layer that composes existing MVP decisions
without hiding them.

The orchestrator is not an executor. It creates an auditable plan from:

- Cache & Reuse Fabric,
- Data Fabric,
- Observations/Forecasting scheduler hints,
- Scheduler/Router,
- Prewarm Planner.

## Flow

```text
request
  ↓
exact cache / reuse check
  ↓ miss
placement decisions
  ↓
data move candidates
  ↓
scheduler hint normalization
  ↓
routing decision
  ↓
prewarm plan
  ↓
orchestration plan
```

## Safety

- Exact cache hit short-circuits execution.
- Data movement remains a plan, not a physical move.
- Routing remains explainable through node scores and reasons.
- Forecast hints are advisory, not mandatory commands.
- The output is serializable with `OrchestrationPlan.as_dict()`.

## Non-goals

- remote execution,
- distributed consensus,
- durable workflow engine,
- DAG scheduler,
- payment/billing optimizer,
- Kubernetes controller.

Those belong later, after the single-node and local multi-node semantics are
stable.
