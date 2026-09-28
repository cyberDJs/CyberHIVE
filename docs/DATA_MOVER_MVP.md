# CyberHIVE Data Mover MVP

## Decision

CyberHIVE Data Fabric needs a dedicated mover before any automatic lifecycle engine may physically relocate files.

The MVP implements a conservative `copy-then-switch` mover:

```text
Data Fabric placement plan
        ↓
Data Mover dry-run
        ↓
validate source + permissions
        ↓
copy to temporary target
        ↓
verify checksum
        ↓
atomic switch
        ↓
audit + optional rollback
```

## Non-goals

This MVP intentionally does not implement:

- distributed copy,
- erasure coding,
- source deletion,
- remote object storage APIs,
- live file locking,
- multi-node consensus,
- streaming partial move resume.

Those are later layers. MVP first proves safety.

## Safety invariants

1. Dry-run never mutates data.
2. Direct destructive move is forbidden.
3. Source file is not deleted by default.
4. Target overwrite is denied unless explicitly allowed.
5. Any overwrite creates a backup before switch.
6. Copied bytes must match source SHA-256.
7. Every plan contains an audit trail.
8. Rollback restores the previous target when a backup exists.

## Placement integration

Patch 004 decides *where data should live*.

Patch 005 starts answering:

> Can this data be moved there safely, and what exact steps would happen?

Later patches should connect `DataMove` objects from `DataFabric` to `DataMoveRequest` objects consumed by `DataMover`.

## Terminology

- **Dry run**: validated plan without mutation.
- **Copy-then-switch**: copy to temp path, verify, then atomically replace target.
- **Backup path**: previous target saved before overwrite.
- **Rollback**: restore previous target from backup or remove newly switched target.

## Block L closeout note

The overwrite failure recovery regression remains part of the hardening gate. If
an overwrite backs up an existing target and a later switch/checksum step fails,
the mover restores the original target before returning failure evidence in the
plan audit.
