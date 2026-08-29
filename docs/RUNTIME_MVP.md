# Runtime MVP

## Scope

Patch 002 introduces the first executable CyberHIVE core primitives:

- `HiveFrame` JSON fallback implementation
- `RuntimeBus`
- `MicroBatcher`
- append-only local `LogStore`
- revisioned `StateEngine`
- in-memory `CacheFabric`
- performance-first `PlacementEngine`

The implementation is intentionally pure Python standard library. No protobuf
compiler, database, message broker or cloud dependency is required for this MVP.

## Flow

```text
Operation
  -> MicroBatcher
  -> HiveFrame
  -> AppendOnlyLog
  -> StateEngine
  -> subscribers
```

## Validation

```bash
PYTHONPATH=src python3 scripts/validate_runtime_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_runtime_bus.py
```

## Current limitations

- JSON frame encoding is a local MVP fallback. The target hot-path wire format remains protobuf or another benchmarked binary format.
- Append-only log is JSONL on local filesystem. It is enough for local validation, not yet a distributed log.
- Cache Fabric is in-memory only.
- Data placement produces recommendations; it does not move files yet.
- No auth, encryption, identity or exposure gateway enforcement is implemented in this patch.

## Next candidates

1. persistent local runtime directory layout,
2. inventory registry loader,
3. exposure gateway policy evaluator,
4. collector for node telemetry,
5. protobuf encoder once tooling is chosen.
