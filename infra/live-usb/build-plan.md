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

### Stage 2 — real build plan

The real build plan defines the next gate without building an image.

Status: implemented as plan by `WB-HIVE-BOOT-0003`.

Boundary markers:

```text
ISO build: NOT EXECUTED
USB write: NOT AUTHORIZED
runtime verification: NOT CLAIMED
ADR accepted: NO
```

### Stage 3 — real image build gate

A developer or isolated runner can attempt an image build from tracked configuration only after the exact build-only approval token is supplied.

Command:

```sh
CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB \
sh infra/live-usb/debian-live/build-real-image.sh
```

Expected output directory:

```text
.cyberhive-live-real-build/
```

Status: gate implemented by `WB-HIVE-BOOT-0004`; real image build execution remains operator-authorized only and is not run by PR validation.

Boundary markers:

```text
ISO build: NOT RUN BY PR
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
ADR accepted: NO
```

### Stage 4 — CI image build candidate

CI validates that the tracked configuration can assemble an image or at least a deterministic root filesystem manifest.

This remains future work and must remain separate from the Stage 1 dry-run wrapper, Stage 2 plan and Stage 3 image build gate.

### Stage 5 — USB boot smoke

Manual evidence proves that the image boots on at least one compatible machine and does not write to internal disks by default.

This remains future work and must produce hardware evidence, not only CI output.

## Artifact names

Proposed pattern:

```text
cyberhive-live-usb-v<version>-<arch>-<date>.iso
cyberhive-live-usb-v<version>-<arch>-<date>.manifest.json
cyberhive-live-usb-v<version>-<arch>-<date>.sha256
cyberhive-live-usb-v<version>-<arch>-<date>.build-log.txt
```

Stage 1 dry-run does not create these artifacts. Stage 2 planning does not create these artifacts. Stage 3 may create these artifacts only after explicit image-only authorization.

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

## Real build manifest

Stage 3 real build manifest path pattern:

```text
.cyberhive-live-real-build/<image-name>.manifest.json
```

Required negative claims even after a successful image build:

```json
{
  "usb_written": false,
  "hardware_booted": false,
  "runtime_verified": false,
  "deployment_performed": false,
  "adr_accepted": false
}
```

## Acceptance evidence

Minimum evidence bundle for a future real image build:

- build command and environment
- source commit
- image hash
- manifest hash sidecar
- build log hash
- package/rootfs manifest when available
- known limitations

Minimum evidence for a future boot smoke test:

- image hash from the real build manifest
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
