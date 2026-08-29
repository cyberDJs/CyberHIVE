# Patch 003 — Inventory + Exposure Gateway MVP

This patch adds:

- `InventoryRegistry`
- `InventoryItem`
- capability model
- independent indexing/access/exposure/sensitivity axes
- `ExposureGateway`
- scoped expiring exposure grants
- validation script
- demo script
- unit tests
- documentation and ADR

## Verify

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_inventory_exposure_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_inventory_exposure.py
```
