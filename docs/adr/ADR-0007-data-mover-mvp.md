# ADR-0007: Data Mover MVP uses copy-then-switch

## Status

Accepted

## Context

Adaptive Data Fabric can decide that an object should move between RAM, NVMe, SSD, HDD, NAS or archive tiers. Executing those decisions unsafely would risk data loss.

## Decision

CyberHIVE will implement a conservative Data Mover MVP using copy-then-switch.

The MVP must support:

- dry-run planning,
- source stat and checksum,
- temporary copy,
- checksum verification,
- atomic target switch,
- overwrite protection,
- backup and rollback,
- audit events.

The mover must not delete source files by default.

## Consequences

Pros:

- safer than direct rename/delete,
- easier to audit,
- rollback-capable,
- usable on local filesystem immediately.

Cons:

- temporarily uses additional disk space,
- large files are copied before becoming active,
- not yet optimized for remote or distributed storage.

## Follow-ups

- Add lock files or leases.
- Add resumable copies.
- Add source cleanup policy.
- Add integration with Data Fabric move plans.
- Add remote backends.
