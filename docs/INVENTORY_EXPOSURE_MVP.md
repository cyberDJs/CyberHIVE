# CyberHIVE Inventory + Exposure Gateway MVP

## Decision

Patch 003 adds the first executable security model for CyberHIVE resources.

The design separates inventory concerns into independent axes:

- `enabled`: whether the resource participates in active operation
- `indexing`: `indexed` or `non_indexed`
- `access`: `allowed`, `gated`, or `denied`
- `exposure`: `private`, `lan`, `authenticated`, or `public`
- `sensitivity`: `public`, `internal`, `sensitive`, or `secret`

This avoids the weak single-status model where a device is merely "allowed" or
"disabled". A resource can be active, non-indexed, gated, and exposed only
through an authenticated gateway.

## Why this matters

A home camera, microphone, sensor, local service, model, document and build
worker are all resources, but they do not share the same security posture.
CyberHIVE therefore needs a common inventory language that agents, skills,
runtime routing and UI can all use.

## Exposure Gateway invariant

Private devices are never exposed directly.

Approved pattern:

```text
private device -> CyberHIVE adapter -> Exposure Gateway -> authenticated grant
```

Rejected pattern:

```text
private device -> public internet
```

Every exposure grant is:

- scoped to one resource,
- scoped to one subject,
- scoped to explicit permissions,
- time-limited,
- auditable,
- non-direct by default.

## Example camera

```yaml
id: camera.frontdoor
kind: camera
enabled: true
indexing: non_indexed
access: gated
exposure: private
sensitivity: sensitive
capabilities:
  - name: video.stream
    permissions:
      - stream.read
  - name: video.snapshot
    permissions:
      - snapshot.read
```

A temporary grant can allow `stream.read` for a user for two hours without
giving direct device access or download permission.

## MVP limitations

- In-memory registry only.
- No real authentication provider yet.
- No network proxy implementation yet.
- No tenant isolation persistence yet.
- No UI yet.

## Next steps

1. Persist inventory in the control-plane store.
2. Add identity provider integration.
3. Add gateway audit log integration with Runtime Bus.
4. Add stream proxy implementation.
5. Add policy-as-code checks for public exposure.
