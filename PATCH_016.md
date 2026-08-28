# Patch 016 — LAN Discovery & Enrollment Handshake MVP

Adds safe local discovery and enrollment handshake contracts.

## Added

- `src/cyberhive_core/lan_discovery.py`
- `scripts/validate_lan_discovery_mvp.py`
- `scripts/demo_lan_discovery.py`
- `tests/test_lan_discovery_mvp.py`
- `schemas/lan-discovery-advertisement.schema.json`
- `schemas/enrollment-handshake.schema.json`
- `docs/NODE_LAN_DISCOVERY_MVP.md`
- `docs/adr/ADR-0018-lan-discovery-enrollment-handshake-mvp.md`

## Validation

Run:

```bash
PYTHONPATH=src python3 scripts/validate_lan_discovery_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_lan_discovery.py
```
