# Codex Post-Merge Hardening — Block L / PATCH_030

## Purpose

Block L follows PR #21 after merge and addresses non-major hardening findings
that were intentionally kept out of the final Block K P1 repair loop.

## Scope

- Worker runtime unsupported-action handling.
- Local resource guard action-specific defaults.
- Worker result payload size enforcement.
- Cache key determinism for unordered collections.
- Data mover overwrite failure recovery remains covered by regression tests and
  documentation.

## Safety boundary

This patch does not introduce shell execution, Docker, SSH, privileged actions,
production access, deployment, force-push, or secret handling.

## Behavioral changes

### Worker Runtime

Unsupported action names are parsed before ACK creation. When parsing fails, the
worker emits a signed denied `ACTION_RESULT` with parse-failure metadata and no
ACK envelope. This prevents an invalid action from stopping controller retries
without a recorded action result.

Result payloads are measured before signing. If the serialized payload exceeds
`WorkerRuntimePolicy.max_result_payload_bytes`, the runtime signs a bounded
failure payload with truncation metadata instead of unbounded handler metadata or
events.

### Resource Guard

`resource_request_for_action_payload()` preserves `default_request_for_action()`
values and then applies explicit payload overrides. Empty prewarm payloads now
reserve the intended prewarm resources instead of falling back to tiny generic
values.

### Cache Reuse

`set` and `frozenset` inputs are canonicalized by sorting recursively stable
representations before hashing.

### Data Mover

The existing overwrite failure restore path remains in the gate through its
regression test. No new physical mover behavior is introduced in Block L.

## Verification target

```text
PYTHONPATH=src python3 -m unittest \
  tests.test_worker_runtime_mvp \
  tests.test_resource_guard_mvp \
  tests.test_cache_reuse_mvp \
  tests.test_data_mover_mvp

PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
PYTHONPATH=src python3 scripts/validate_cache_reuse_mvp.py
PYTHONPATH=src python3 scripts/validate_data_mover_mvp.py
PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
```
