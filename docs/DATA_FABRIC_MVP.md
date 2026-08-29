# CyberHIVE Adaptive Data Fabric MVP

## Decision

Patch 004 turns the early Patch 002 placement score into an executable Adaptive
Data Fabric MVP.

The goal is not to copy cloud storage pricing tiers. The goal is to place data
where it should physically live for the current and predicted workload.

## Adds

- `DataFabric`
- `DataObjectRegistry`
- `StorageDevice`
- `AccessRecord`
- `DataProfile`
- `DataMove`
- `PlacementAction`
- behavior-driven `PlacementEngine`
- migration planning
- tier usage reporting

## Storage tiers

```text
L1  RAM
L2  local NVMe
L3  local SSD
L4  HDD / RAID
L5  NAS / distributed storage
L6  archive / remote object storage
```

## Placement inputs

Placement is driven by:

- recent reads,
- 24h reads,
- write pressure,
- predicted use,
- latency requirement,
- fanout / exclusivity,
- reconstruction cost,
- preferred node locality,
- sensitivity,
- current tier and replica count,
- device capacity and pressure.

Monetary cost is deliberately not part of the default score.

## Flow

```text
Access observations
    -> DataProfile
    -> Temperature score
    -> Placement decision
    -> Migration plan
    -> later: actual mover
```

## Examples

A model repeatedly used by multiple workers is promoted:

```text
HDD -> RAM/NVMe
```

A stale raw video archive is demoted:

```text
NVMe -> HDD/archive
```

Secret local cache remains local and single-replica:

```text
archive/public path rejected -> local NVMe
```

## Current MVP limitation

Patch 004 produces decisions and migration plans. It does not physically move
files yet. That is intentional: the next step should add a safe mover with
checksum verification, dry-run mode and rollback.

## Validate

```bash
PYTHONPATH=src python3 scripts/validate_data_fabric_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_data_fabric.py
```
