# PATCH_030 — Block L Post-Merge Hardening

## Summary

Block L hardens the merged PR #21 baseline without deployment or production
changes.

## Changes

- Parse worker action names before ACK emission.
- Return a signed denied result for unsupported actions without ACKing them.
- Apply action-specific resource defaults before explicit payload overrides.
- Enforce `WorkerRuntimePolicy.max_result_payload_bytes` on signed result
  payloads.
- Canonicalize unordered collections before cache-key hashing.
- Preserve Data Mover overwrite failure recovery as a documented regression gate.

## Safety

No shell, Docker, SSH, sudo, deployment, production access, force-push, or secret
handling is introduced.
