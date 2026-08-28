# CyberHIVE Patch 002 - Runtime MVP

This patch adds the first executable CyberHIVE runtime primitives.

## Adds

- `src/cyberhive_core/`
- `scripts/validate_runtime_mvp.py`
- `scripts/demo_runtime_bus.py`
- `tests/test_runtime_mvp.py`
- `docs/RUNTIME_MVP.md`
- `docs/adr/ADR-0003-runtime-bus-mvp.md`
- `docs/adr/ADR-0004-local-storage-mvp.md`

## Validate

```bash
PYTHONPATH=src python3 scripts/validate_runtime_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_runtime_bus.py
```

## Commit

```bash
git add .
git commit -m "Add CyberHIVE Runtime Bus MVP"
```
