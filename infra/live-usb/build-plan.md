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

### Stage 1 — local dry build

A developer can build an ISO/image locally from tracked configuration.

### Stage 2 — CI dry build

CI validates that the tracked configuration can assemble an image or at least a deterministic root filesystem manifest.

### Stage 3 — USB boot smoke

Manual evidence proves that the image boots on at least one compatible machine and does not write to internal disks by default.

## Artifact names

Proposed pattern:

```text
cyberhive-live-usb-v<version>-<arch>-<date>.iso
cyberhive-live-usb-v<version>-<arch>-<date>.manifest.json
cyberhive-live-usb-v<version>-<arch>-<date>.sha256
```

## Acceptance evidence

Minimum evidence bundle:

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

## Non-goals for v0.1

- Secure Boot signing
- GPU inference
- mobile worker runtime
- public federation
- autonomous updates
- destructive rescue operations
