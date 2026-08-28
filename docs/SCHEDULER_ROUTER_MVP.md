# CyberHIVE Scheduler + Router MVP

## Purpose

The Scheduler + Router MVP turns telemetry and forecast hints into concrete routing decisions.

It does not execute workloads. It answers:

- which node should receive this workload,
- whether the workload should be queued or rejected,
- whether the selected node needs prewarming,
- which alternatives were considered,
- why the decision was made.

## Core objects

- `NodeState` — schedulable capacity and current pressure of a node.
- `WorkloadRequest` — a unit of work that needs placement.
- `SchedulerHintImpact` — normalized hints from the forecasting layer.
- `ComputeRouter` — deterministic scoring and routing.
- `PrewarmPlanner` — prepares model/runtime prewarm plans.

## Decision inputs

The router considers:

- node health,
- enabled/disabled state,
- required capabilities,
- labels,
- CPU headroom,
- RAM headroom,
- VRAM headroom,
- GPU utilization,
- queue depth,
- latency,
- data locality,
- preferred and avoided nodes,
- scheduler hints.

## Safety rules

Interactive workloads must preserve VRAM headroom. A node that would violate the interactive reserve is not eligible.

Forecasting hints are advisory, not absolute. A critical workload can still route through a node with `hold_capacity`; normal and low-priority work should respect the hint.

## Non-goals

- distributed consensus,
- container execution,
- Kubernetes replacement,
- long-term scheduling history,
- real billing/cost optimization,
- hard real-time guarantees.

## Next steps

Patch 009 should connect the router to the runtime bus and produce route decisions from actual observed node state.
