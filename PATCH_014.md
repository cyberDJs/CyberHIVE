# Patch 014 — Node Enrollment & Identity MVP

## Summary

Adds the first CyberHIVE node identity boundary.

The MVP introduces bootstrap-token based enrollment, signed enrollment requests,
public-key fingerprints, trust states, node sessions, quarantine/revoke flows and
Node Agent descriptor conversion.

## Added

- `src/cyberhive_core/node_identity.py`
- `tests/test_node_identity_mvp.py`
- `scripts/validate_node_identity_mvp.py`
- `scripts/demo_node_identity.py`
- `schemas/node-enrollment-request.schema.json`
- `docs/NODE_IDENTITY_MVP.md`
- `docs/adr/ADR-0016-node-enrollment-identity-mvp.md`

## Security posture

This is intentionally not full PKI, mTLS or attestation yet.

It does provide:

- one-time/limited-use bootstrap tokens,
- HMAC proof over canonical enrollment payload,
- no storage of cleartext bootstrap secrets,
- stable public-key fingerprints,
- duplicate node/fingerprint rejection,
- short-lived node session grants,
- explicit trust states: enrolled, quarantined, revoked.

## Validation

Expected full repo result after Patch 002–014:

```text
Ran 83 tests
OK
```
