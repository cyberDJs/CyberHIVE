# CyberHIVE Live USB Build Plan

## Build objective

Create a reviewable, reproducible-enough bootable image for the first CyberHIVE Live USB.

The first image only has to prove the runtime surface and safety model. It does not have to provide production inference or a public swarm.

## Candidate builder

Primary candidate for v0.1:

- Debian live-build or equivalent live-image tooling

Later candidate once runtime contents stabilize:

- NixOS ISO for stronger declarative reproducibility

## Image contents v0.1

Required:

- CyberHIVE branded boot splash or role selector placeholder
- role selector contract
- local health endpoint or health command
- hardware inventory command
- log/evidence directory
- explicit persistent overlay policy
- disabled-by-default DevBridge placeholder
- clear safety banner

Optional:

- local web dashboard mock endpoint
- cache directory layout
- network diagnostics
- QR/local URL for dashboard

## Build stages

### Stage 0 — repository skeleton

Documentation and layout only. No image build required.

Status: completed by `WB-HIVE-BOOT-0001`.

### Stage 1 — build dry-run

A developer or CI runner can check tracked build inputs and produce a manifest without creating an image.

Command:

```sh
sh infra/live-usb/debian-live/build-dry-run.sh
```

Expected output:

```text
.cyberhive-live-build-dry-run/manifest.json
```

This stage may determine whether the live-build command is visible on the runner, but it must not call it.

Status: implemented by `WB-HIVE-BOOT-0002`.

### Stage 2 — local dry build

A developer can build an ISO/image locally from tracked configuration.

This remains future work. It requires a separate work block, explicit build evidence and a hashable output artifact.

### Stage 3 — CI dry build

CI validates that the tracked configuration can assemble an image or at least a deterministic root filesystem manifest.

This remains future work and must remain separate from the Stage 1 dry-run wrapper.

### Stage 4 — USB boot smoke

Manual evidence proves that the image boots on at least one compatible machine and does not write to internal disks by default.

This remains future work and must produce hardware evidence, not only CI output.

## Artifact names

Proposed pattern:

```text
cyberhive-live-usb-v<version>-<arch>-<date>.iso
cyberhive-live-usb-v<version>-<arch>-<date>.manifest.json
cyberhive-live-usb-v<version>-<arch>-<date>.sha256
```

Stage 1 dry-run does not create these artifacts. It only creates a dry-run manifest.

## Dry-run manifest

Stage 1 dry-run manifest path:

```text
.cyberhive-live-build-dry-run/manifest.json
```

Required negative claims:

```json
{
  "build_executed": false,
  "iso_created": false,
  "usb_written": false,
  "runtime_verified": false
}
```

## Acceptance evidence

Minimum evidence bundle for a future real image build:

- build command and environment
- image hash
- package/rootfs manifest
- boot target hardware summary
- boot mode: UEFI/BIOS
- network state
- health result
- hardware inventory output
- internal disk write boundary observation
- known limitations

Minimum evidence for Stage 1 dry-run:

- source branch/commit
- dry-run command
- generated dry-run manifest
- CI job result
- confirmation that no image/media/runtime verification claim was made

## Non-goals for v0.1

- Secure Boot signing
- GPU inference
- mobile worker runtime
- public federation
- autonomous updates
- destructive rescue operations
