# ADR-0009 — CyberHIVE Live Appliance Local Control Plane

## Status

Proposed

File existence is not acceptance.

## Context

The first physical CyberHIVE Live USB boot proved the image can reach a local shell, but also showed that shell-only operation is not an adequate appliance UX. The image lacked an SSH server and required manual network discovery.

CyberHIVE already defines web administration as the primary operator surface. A separate local desktop administration implementation would duplicate security and control logic.

## Decision

For Live Appliance v0.2:

1. Use one local browser control plane as the primary appliance UI.
2. Advertise it as `http://cyberhive.local` using mDNS, with detected IPv4 fallback.
3. Require a boot-session pairing code before browser control actions.
4. Include SSH server by default with root login disabled.
5. Use key-first SSH bootstrap from a read-only `CYBERHIVE_CFG` medium; if no key is available, generate an ephemeral boot password.
6. Keep the live root ephemeral/read-only by default and make persistence state explicit.
7. Add a host-disk guard that detects unexpected writable internal-disk mounts without silently mutating disks.
8. Keep remote help, MCP and DevBridge disabled until separate explicit local enablement.
9. Build later desktop/prompt UX on the same web UI/API instead of creating a second control plane.

## Consequences

Positive:

- LAN onboarding requires no cloud account.
- headless and local-desktop use share one control plane.
- SSH works on first boot without embedding a reusable default password.
- operators can pre-seed trusted public keys without remastering the image.
- security state becomes visible rather than implicit.

Negative:

- the image gains network-facing services and therefore a larger attack surface.
- mDNS and HTTP require explicit hardening and runtime tests.
- ephemeral password fallback is weaker than key-only mode and must be local-session scoped.
- a config-media provisioning workflow is still required for polished key-first deployments.

## Alternatives considered

### SSH disabled by default

Rejected for v0.2 because the physical appliance is explicitly intended for LAN administration and the first hardware test showed the operational cost of a missing server.

### Permanent default password

Rejected because it creates a reusable credential across every copy of the image.

### Desktop-first administration

Rejected because it duplicates the browser control plane and adds significant image/runtime complexity before the local API stabilizes.

### Cloud-first enrollment

Rejected for the Live Appliance baseline because offline/local-first operation is a core product principle.

## Rollback

Remove the v0.2 browser/SSH/bootstrap units and packages, restore the v0.1 package seed and static MOTD, and keep the already-proven image-build gate intact.

## Acceptance required

This ADR remains proposed until the implementation is reviewed and physical v0.2 runtime evidence passes.

```text
ADR-0009 accepted: NO
```
