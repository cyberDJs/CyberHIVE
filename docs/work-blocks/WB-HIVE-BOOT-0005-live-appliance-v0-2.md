---
id: WB-HIVE-BOOT-0005
type: work-block
status: implementation
---

# WB-HIVE-BOOT-0005 — CyberHIVE Live Appliance v0.2

## Source of truth

- Repository: `cyberDJs/CyberHIVE`
- Stacked base: PR #27 exact head `63c14dba7fd28b8a0d53c23bbda766b06d950260`
- Parent gate: `WB-HIVE-BOOT-0004 — Real Image Build Gate`
- Physical follow-on evidence: `docs/evidence/WB-HIVE-BOOT-0004-physical-boot-2026-09-03.md`

## Problem

The v0.1 image proved that CyberHIVE can be built, written to removable media and physically booted, but the physical session exposed important product gaps:

- no SSH server was installed
- operator instructions were static and required manual `ip` commands
- no browser-first control surface existed
- no QR/local pairing flow existed
- runtime branding was text-only
- host-disk protection was stated but not surfaced as machine-readable runtime evidence

## User decisions incorporated

- CyberDJS branding must be visible during boot
- browser-first control from another LAN computer is required
- SSH uses option 3C: key-first from removable config media, otherwise a temporary boot password
- first-boot wizard: yes
- QR onboarding: yes
- immutable/resettable model: yes
- automatic network discovery/instructions: yes
- support/evidence bundle: yes
- remote-help/pairing foundation: yes, disabled by default
- desktop/prompt surface: planned after the browser control plane; reuse the same UI/API

## Net improvement

The Live USB becomes a usable local appliance instead of a shell-only proof. Operators can discover it, pair to it, inspect it and SSH to it without preconfigured cloud infrastructure, while the security boundary remains visible and local-first.

## Implementation slices

### Slice A — boot and secure local access

- reviewable CyberDJS/CyberHIVE boot graphic source
- deterministic boot raster export during build
- `openssh-server`
- root SSH login disabled
- `CYBERHIVE_CFG` read-only key import
- ephemeral password fallback
- dynamic local welcome + QR
- mDNS advertisement

### Slice B — browser control plane

- local HTTP service
- boot-session pairing code
- overview/network/SSH/health/inventory surfaces
- role selection records boot-session intent
- remote-help visible but disabled by default

### Slice C — safety and evidence

- host-disk guard
- immutable/persistence state reporting
- support bundle
- exact runtime/build/session identity

### Later slice — desktop/prompt profile

- optional lightweight desktop
- launch same local web UI in app/kiosk mode
- prompt -> plan -> approval -> execution -> evidence workflow

## Security boundaries

- no root SSH login
- no baked private key/password/pairing secret
- config media is read-only
- temporary password and pairing code rotate each boot
- temporary password is displayed only on a physical TTY
- browser control actions require pairing
- DevBridge/MCP remain disabled unless separately authorized
- remote help remains disabled unless separately authorized
- host-disk guard is detection/evidence, not a destructive remount or repair engine
- no host-disk write is authorized by this work block

## Acceptance criteria

Repository acceptance:

- implementation and docs agree on defaults
- static validation passes
- shell and Python syntax checks pass
- CI passes on the exact PR head
- no unresolved review findings

Runtime acceptance requires a newly built image and separate physical evidence for:

- boot graphic
- dynamic console URL/QR
- `cyberhive.local`
- browser pairing
- SSH key mode
- SSH password fallback
- host-disk guard
- support bundle
- session credential rotation after reboot

## Promotion boundary

This work block may create code, tests, docs and a draft PR. It does not authorize:

- merge
- USB rewrite with a new v0.2 image
- physical boot claims for v0.2
- production deployment
- MCP/DevBridge enablement
- remote-help enablement
- ADR acceptance
