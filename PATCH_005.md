# Patch 005 — Data Mover MVP

Adds a safe, auditable data mover for CyberHIVE Adaptive Data Fabric.

## Purpose

Patch 004 can produce placement and migration plans. Patch 005 introduces the first execution layer:

- dry-run move plans,
- source validation,
- SHA-256 checksums,
- copy-then-switch workflow,
- overwrite protection,
- optional backup for overwrite,
- rollback for switched targets,
- audit trail,
- tests and demo.

## Safety rule

The mover does not delete the source by default. A data move is treated as:

1. validate source,
2. copy to temporary target,
3. verify checksum,
4. atomically switch target into place,
5. keep source until a later cleanup policy approves deletion.
