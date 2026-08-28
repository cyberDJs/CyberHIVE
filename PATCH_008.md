# Patch 008 — Scheduler + Router MVP

This patch adds the first CyberHIVE scheduling layer.

## Added

- `ComputeRouter`
- `NodeState`
- `WorkloadRequest`
- `SchedulerHintImpact`
- `PrewarmPlanner`
- route decisions with alternatives and reasons
- forecast-aware scheduler hint handling
- interactive VRAM reserve enforcement
- capability, label and data affinity matching
- demo, validation, tests and ADR

## Validation

```bash
PYTHONPATH=src python3 scripts/validate_scheduler_router_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_scheduler_router.py
```

## Commit message

```text
Add CyberHIVE Scheduler and Router MVP
```
