# Patch 007 — Observations + Telemetry + Forecasting MVP

This patch adds the first adaptive feedback layer for CyberHIVE.

## Adds

- `src/cyberhive_core/observations_forecasting.py`
- `scripts/validate_observations_forecasting_mvp.py`
- `scripts/demo_observations_forecasting.py`
- `tests/test_observations_forecasting_mvp.py`
- `docs/OBSERVATIONS_FORECASTING_MVP.md`
- `docs/adr/ADR-0009-observations-telemetry-forecasting-mvp.md`
- `schemas/observation-v2.schema.json`
- `schemas/scheduler-hint.schema.json`

## Validation

```bash
PYTHONPATH=src python3 scripts/validate_observations_forecasting_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_observations_forecasting.py
```
