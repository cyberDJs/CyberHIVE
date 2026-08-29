# Patch 006 — Cache & Reuse Fabric MVP

This patch adds the first reusable computation layer for CyberHIVE.

It answers one core runtime question:

> Do we really need to compute this again?

## Added

- `src/cyberhive_core/cache_reuse.py`
- `scripts/validate_cache_reuse_mvp.py`
- `scripts/demo_cache_reuse.py`
- `tests/test_cache_reuse_mvp.py`
- `docs/CACHE_REUSE_FABRIC_MVP.md`
- `docs/adr/ADR-0008-cache-reuse-fabric-mvp.md`
- `schemas/cache-reuse-entry.schema.json`

## Capabilities

- canonical operation fingerprints,
- exact result cache,
- semantic intent cache,
- state cache,
- artifact metadata cache,
- execution pattern memory,
- sensitivity-aware cache policy,
- TTL and dependency invalidation,
- resource-cost based reuse decisions.

## Non-goals

- distributed cache coherence,
- persistent cache database,
- automatic vector similarity search,
- LLM-based plan generation,
- monetary price optimization.
