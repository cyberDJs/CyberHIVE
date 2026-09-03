# CyberHIVE Live USB Runtime Surface

## Purpose

Define the visible and operational surface of the CyberHIVE Live USB and the v0.2 Live Appliance.

The runtime must make the node understandable at boot time: what it is, how to reach it, what security mode is active, what it can do, and what it will not do without explicit enablement.

## Required surfaces

### Boot branding

The boot experience must show CyberDJS/CyberHIVE identity before the operator reaches a shell.

Requirements:

- reviewable source asset under `assets/brand/runtime/`
- deterministic build export for the bootloader
- image version/build identity
- Live Appliance label
- usable text fallback when graphics are unavailable

The source asset is versioned; generated build output is not treated as a new source of truth.

### Dynamic local welcome screen

After boot the local console shows:

- CyberDJS / CyberHIVE identity
- hostname
- detected IPv4 address when available
- `http://cyberhive.local`
- fallback URL using the IPv4 address
- SSH connect string
- SSH authentication mode (`key` or `ephemeral-password`)
- ephemeral password only on a local physical TTY when password mode is active
- browser pairing code only on a local physical TTY
- QR code to the local web UI when `qrencode` is available
- host-disk guard status
- DevBridge/MCP state
- remote-help state

Secrets must not be printed to remote SSH pseudo-terminals.

### SSH 3C bootstrap

At each boot:

1. Look for a filesystem labeled `CYBERHIVE_CFG`.
2. Mount it read-only with `nodev,nosuid,noexec`.
3. If a valid `authorized_keys` file exists, install it for the `cyberhive` user and disable SSH password authentication.
4. Otherwise generate an ephemeral boot password, set it only for the `cyberhive` account, and show it only on the local console.
5. Root SSH login remains disabled in both modes.

No private SSH key is embedded into the image.

### Browser control plane

Primary operator URL:

```text
http://cyberhive.local
```

Fallback:

```text
http://<detected-ipv4>
```

Minimum v0.2 cards/surfaces:

- Overview
- Setup / role selection
- Network
- SSH mode
- Health
- Hardware inventory
- Host-disk guard
- Support/evidence bundle
- Remote Help status

The browser control plane uses a boot-session pairing code before control actions. Read-only status may be visible before pairing; write/control actions require pairing.

### First-boot role selector

Roles:

- Controller + Worker
- Worker Only
- DevBridge Mode (explicit enable required)
- Offline Diagnostics
- Rescue / Hardware Inventory

The v0.2 role selection records boot-session intent. It must not silently enable MCP, DevBridge, host-disk writes or remote help.

### Health endpoint or command

Machine-readable surfaces:

```text
cyberhive-live-health
GET /api/health
```

Future product compatibility target:

```text
cyberhive health
```

Health includes at least:

- runtime status
- live version
- hostname/IP
- SSH service/auth mode
- web service
- host-disk guard state
- DevBridge/MCP state
- remote-help state
- ephemeral root/persistence state

### Hardware inventory

Hardware inventory should report capabilities, not just labels.

Capability dimensions:

- CPU
- GPU/NPU where available
- RAM
- storage devices and transport
- network interfaces/link state
- platform and architecture
- current kernel

### Support/evidence bundle

One command produces a bounded support archive containing:

- health output
- hardware inventory
- network summary
- block-device/mount summary
- selected service state
- bounded recent logs
- build/session identity where available

It must exclude SSH private keys, temporary passwords, pairing tokens and other authentication material.

### Host-disk guard

The default Live Appliance must not mount internal fixed disks read-write as part of normal boot.

The guard reports unexpected writable mounts backed by non-removable physical disks and produces machine-readable evidence. The first implementation is detection/fail-closed evidence, not an implicit disk-repair or remount engine.

### Remote help

Remote help is a separate capability from LAN browser control.

Default:

```text
remote help: disabled
```

Future enabling requires an explicit local action, a bounded session identity and audit evidence.

### Local desktop and prompt surface

A future optional desktop profile reuses the same local web UI/API instead of implementing a second administration stack.

Target local prompt surface:

- prompt composer
- plan preview
- approval boundary
- execution state
- evidence/receipts
- model/runtime selector

The desktop is not required for v0.2 acceptance.

## Local-first behavior

The runtime remains useful without internet access:

- local console and web UI
- SSH on LAN
- local health/inventory
- support bundle
- offline diagnostics
- local role selection

## Anti-goals

The runtime surface must not hide:

- whether SSH password mode is active
- whether DevBridge/MCP is enabled
- whether remote help is enabled
- whether persistence is active
- whether internal disks are mounted
- whether the node is enrolled or anonymous
- whether network links are degraded
