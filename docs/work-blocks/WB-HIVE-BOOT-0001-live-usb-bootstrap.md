---
id: WB-HIVE-BOOT-0001
type: work-block
title: CyberHIVE Live USB Bootstrap
status: proposed
owner: CyberHIVE
created: 2026-09-02
updated: 2026-09-02
scope: repository-only planning
---

# WB-HIVE-BOOT-0001 — CyberHIVE Live USB Bootstrap

## Problem

CyberHIVE needs a first tangible runtime artifact: a bootable live USB image that can start a CyberHIVE node on owned or borrowed hardware without installing to, mutating, or trusting the host disk.

This work block deliberately treats the live USB as the first practical product surface for the CyberHIVE fabric, not as a narrow Linux-only product boundary.

## Intent

Create the repository baseline for a CyberHIVE Live USB that can later be built, written to a USB drive, booted on compatible hardware, and used as:

1. controller + worker,
2. worker only,
3. DevBridge / MCP development node,
4. offline diagnostics node,
5. rescue and hardware-inventory node.

## Product principle

CyberHIVE is a multi-platform peer-to-peer AI/compute/cache fabric.

A Linux live USB is the first portable bootstrap artifact, not the only supported platform. The worker model must remain capability-first and support future peers across:

- Linux,
- macOS,
- Windows,
- Android,
- iOS / iPadOS where platform limits allow,
- watchOS-constrained micro-peers,
- Raspberry Pi / ARM Linux,
- NAS and edge devices,
- VPS and optional cloud infrastructure.

The scheduler must not ask whether a peer is a specific operating system or GPU class. It must ask what the peer can safely do right now.

## Scope

This work block defines the live USB bootstrap target, branding/runtime surface, security boundaries, acceptance checks, and next implementation slices.

Initial planning scope:

- live USB target definition,
- boot role selector contract,
- runtime branding and UI requirements,
- non-destructive host safety boundary,
- persistent overlay policy,
- hardware inventory and capability model seed,
- DevBridge / MCP safety boundary,
- weak-network and failure-first assumptions,
- repository layout proposal for future build scripts and image assets.

## Non-goals

This block does not authorize or implement:

- production deployment,
- public marketplace,
- cryptocurrency incentives,
- global federation,
- destructive host-disk operations,
- automatic remote access,
- baked-in secrets,
- trusted anonymous compute,
- mandatory Kubernetes,
- mandatory desktop environment,
- hardware-specific product narrowing to RTX or any one platform.

## Runtime modes

### Controller + Worker

Boots the local node as a fabric controller and local worker. It may coordinate local peers, expose the local web/API surface, and contribute local compute/cache/services.

### Worker Only

Boots as a participant that contributes capabilities to an enrolled controller. It must not assume trust merely because it sees a controller on the LAN.

### DevBridge Mode

Boots an explicitly enabled development bridge for controlled repository work, diagnostics, logs, test execution, and later MCP integration.

DevBridge must remain opt-in after boot and must not expose unrestricted shell execution in the first implementation.

### Offline Diagnostics

Runs local checks, hardware inventory, storage/cache diagnostics, and log collection without joining a fabric.

### Rescue / Hardware Inventory

Provides safe boot tooling to inspect the machine and export inventory/evidence without writing to internal disks by default.

## Branding and runtime UX

CyberHIVE branding is part of the runtime, not a post-build skin.

The live environment should include:

- CyberHIVE boot splash,
- branded boot role selector,
- local runtime dashboard,
- topology/fabric view,
- hardware inventory view,
- cache health view,
- network health view,
- DevBridge/MCP status view,
- logs/evidence view,
- consistent hexagon/hive visual language,
- dark high-contrast theme with cyan/teal/blue highlights,
- clear local-first, peer-to-peer, aggressive-cache, weak-network and failure-aware messaging.

## Network and failure assumptions

CyberHIVE must treat weak and unreliable environments as normal.

Baseline assumptions:

- 100 Mbps LAN may be normal,
- Wi-Fi loss may happen,
- nodes may shut down without warning,
- batteries may run low,
- devices may thermal-throttle,
- disks may be unavailable or corrupt,
- model loading may fail,
- overlays may partition,
- mobile platforms may suspend background work,
- capability state may become stale.

Design principles:

- send tasks and intent before large raw state,
- prefer data/model locality,
- cache aggressively,
- verify cache content by digest before trusting it,
- batch telemetry,
- use delta sync where practical,
- preserve partial state and resume safely,
- degrade instead of globally restarting.

## Security boundary

Required invariants:

1. no secrets baked into the ISO/image,
2. no automatic inbound remote access,
3. no write to internal disks by default,
4. no peer trusted only because it is on LAN,
5. no MCP/SSH/DevBridge exposure without explicit local enablement,
6. no destructive commands in the first DevBridge slice,
7. all future enrollment and identity material must be revocable,
8. persistent overlay must be explicit and inspectable,
9. evidence/log export must avoid secrets by default.

## Candidate technical direction

Initial build candidate: Debian live-build or equivalent reproducible live-image tooling.

NixOS remains a strong later candidate for a more reproducible declarative image once the live USB contents and runtime contracts stabilize.

This work block does not finalize the base OS. It defines the artifact goal and acceptance boundary.

## Acceptance criteria

The first implementation derived from this block is acceptable when:

- a bootable image can be built reproducibly enough for review,
- the image can be written to USB by documented steps,
- the live environment boots on at least one compatible x86_64 machine,
- it does not write to internal disks by default,
- it displays CyberHIVE branding during boot or role selection,
- it exposes a local `/health` endpoint or equivalent health command,
- it captures hardware inventory,
- it stores logs/evidence in RAM or explicit persistent overlay,
- it can run in at least one selected runtime mode,
- safety boundaries and known limitations are documented.

## Proposed repository changes in first PR

- `docs/work-blocks/WB-HIVE-BOOT-0001-live-usb-bootstrap.md`
- `docs/runbooks/live-usb-bootstrap.md`
- `docs/architecture/live-usb-runtime-surface.md`
- `docs/security/live-usb-threat-model.md`
- `docs/ux/cyberhive-runtime-branding.md`
- optional placeholders under `infra/live-usb/`
- optional placeholders under `assets/brand/runtime/`

## Tests and verification plan

Planning-only PR:

- documentation consistency check,
- no secret material check,
- no runtime mutation.

Implementation PRs:

- image build dry-run,
- file manifest verification,
- boot smoke test evidence,
- hardware inventory fixture tests,
- role selector behavior tests,
- DevBridge disabled-by-default test,
- no-internal-disk-write safety check where practical.

## Rollback

Repository-only rollback is removal or supersession of this work-block documentation.

Runtime rollback for later implementation must include:

- boot without persistent overlay,
- wipe/reset overlay state,
- reset enrollment state,
- export logs before wipe,
- safe shutdown.

## Unresolved questions

- base image builder: Debian live-build vs NixOS ISO vs other,
- persistent overlay format and encryption policy,
- first DevBridge implementation boundary,
- whether MCP server ships disabled in-image or is fetched/enabled after boot,
- secure enrollment UX for offline/weak networks,
- Secure Boot support target for first image,
- minimum USB size and write tool support matrix,
- exact relationship between live USB role selector and later mobile/desktop worker apps.
