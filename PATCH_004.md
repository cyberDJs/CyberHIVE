# Patch 004 — Adaptive Data Fabric MVP

This patch upgrades CyberHIVE storage thinking from static tiers to
behavior-driven data placement.

## Adds

- `DataFabric`
- `DataObjectRegistry`
- `StorageDevice`
- `AccessRecord`
- `DataProfile`
- `DataMove`
- `PlacementAction`
- migration planning
- tier usage reporting
- validation script
- demo script
- unit tests
- documentation and ADR

## Verify

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_data_fabric_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_data_fabric.py
```

## Commit

```bash
git add .
git commit -m "Add CyberHIVE Adaptive Data Fabric MVP"
```
