# CyberHIVE Live USB Build Plan

## Build objective

Create a reviewable, reproducible-enough bootable image for the CyberHIVE Live Appliance while keeping media writes, runtime exposure and promotion as separate evidence gates.

## Candidate builder

Current proven candidate:

- Debian 12/bookworm live-build

Later candidate once runtime contents stabilize:

- NixOS ISO may be evaluated for stronger declarative reproducibility

## Build stages

### Stage 0 — repository skeleton

Status: completed by `WB-HIVE-BOOT-0001`.

### Stage 1 — build dry-run

Status: implemented by `WB-HIVE-BOOT-0002`.

### Stage 2 — real build plan

Status: implemented by `WB-HIVE-BOOT-0003`.

### Stage 3 — real image build gate

Status: gate implemented by `WB-HIVE-BOOT-0004`.

An explicit image-only build was executed from PR #27 exact head `63c14dba7fd28b8a0d53c23bbda766b06d950260` and preserved as workflow evidence.

The gate still does not itself grant USB write, boot, deployment or ADR authority.

### Stage 4 — media write evidence

Status: physically exercised 2026-09-03 outside the PR #27 build-only boundary.

Observed evidence:

- source ISO SHA-256 `a93778f299031a0eab340f75e95ed600c5cef315c0678929b36b093ccb023b49`
- source image size `861929472` bytes
- removable target positively identified before write
- `dd` completed successfully
- byte-for-byte `cmp -n 861929472` returned success
- media was ejected after verification

This observation is evidence of that execution only. Repository automation must not silently generalize it into permission to write future media.

### Stage 5 — USB physical boot smoke

Status: physically exercised 2026-09-03.

Observed console evidence showed:

- Debian GNU/Linux 12 `cyberhive-live`
- x86_64 kernel boot
- CyberHIVE Live USB MOTD
- automatic `cyberhive` login
- shell reached successfully
- network interface acquired IPv4 `192.168.1.122/24` in the photographed session
- SSH server was absent in the v0.1 image (`ssh.service` / `sshd.service` not found)

The boot proof closes the basic physical-boot question and opens `WB-HIVE-BOOT-0005` for appliance UX and local-control hardening.

### Stage 6 — Live Appliance v0.2

Work block: `WB-HIVE-BOOT-0005`.

Required image behavior:

- CyberDJS/CyberHIVE boot branding
- SSH server included and enabled
- key-first `CYBERHIVE_CFG` bootstrap with ephemeral password fallback
- mDNS `cyberhive.local`
- browser-first local control surface
- local pairing code
- dynamic TTY instructions and QR onboarding
- first-boot role wizard
- immutable/read-only live-root policy made visible
- host-disk guard evidence
- support bundle
- remote-help disabled by default
- build/session identity visible to the operator

### Stage 7 — optional desktop/prompt profile

A later profile adds a lightweight desktop that opens the same browser control plane locally and adds the prompt/plan/approval/evidence experience. It does not fork the control-plane implementation.

## Runtime graphic pipeline

The canonical runtime graphic source is a reviewable SVG under:

```text
assets/brand/runtime/
```

The image build converts that source to the bootloader's required raster format inside the temporary build workspace. Generated boot raster output is not committed as the source of truth.

For Debian live-build, bootloader customization is staged through `config/bootloaders` in the temporary build tree.

## Configuration media contract

Optional operator configuration is discovered by filesystem label:

```text
CYBERHIVE_CFG
```

The Live Appliance mounts this medium read-only and may import:

```text
authorized_keys
```

Private keys, passwords and enrollment secrets must never be baked into the ISO.

## Acceptance evidence for v0.2

Minimum repository/CI evidence:

- validation of required packages and units
- shell syntax validation
- Python syntax validation for local web service
- validation that root SSH login is disabled
- validation that key mode disables SSH password authentication
- validation that config media is mounted read-only
- validation that host-disk guard contains no disk mutation commands
- validation that remote help / DevBridge / MCP defaults stay disabled
- validation that boot graphic source exists and deterministic export tooling is required

Minimum future physical evidence:

- branded boot screen
- `cyberhive.local` resolution from another LAN device
- browser pairing and health page
- SSH key-mode acceptance
- SSH password-fallback acceptance
- host-disk guard PASS with block/mount evidence
- support bundle generation
- restart proves ephemeral credentials/session state rotate

## Non-goals for v0.2

- production inference
- public federation
- autonomous updates
- unattended remote support
- destructive rescue operations
- host-disk writes
- production deployment
- ADR auto-acceptance
