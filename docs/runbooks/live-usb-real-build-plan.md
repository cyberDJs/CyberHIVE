# CyberHIVE Live USB Real Build Plan Runbook

## Status

Planning gate only. No image build is performed by this runbook.

## Purpose

Define the safe path from the Debian Live candidate to the first real CyberHIVE Live USB image build.

This runbook is the operator contract for a later build work block. It is not a build receipt.

## Preconditions for a later real build

A later real build requires all of the following:

1. explicit user authorization bound to a source commit,
2. a clean source branch or exact merge commit,
3. an isolated Linux builder environment,
4. no repository credentials in the builder workspace,
5. no DevBridge, MCP or inbound remote control enabled,
6. a dedicated output directory ignored by Git,
7. a plan for capturing logs, hashes and package/rootfs evidence.

## Build target

Initial target:

```text
infra/live-usb/debian-live
```

Expected output family for a later build:

```text
cyberhive-live-usb-v0.1-amd64-<date>.iso
cyberhive-live-usb-v0.1-amd64-<date>.manifest.json
cyberhive-live-usb-v0.1-amd64-<date>.sha256
cyberhive-live-usb-v0.1-amd64-<date>.build-log.txt
```

## Later build phases

### Phase A — build authorization

Record the exact source commit, builder identity label and output directory.

No build may start from an unbound branch name alone.

### Phase B — builder preparation

Prepare a disposable Linux builder.

The builder may resolve package repositories required by the selected live-image toolchain, but must not fetch arbitrary project code outside the checked-out repository state.

### Phase C — image build

Run the selected live-image toolchain only after authorization.

The build result is an image artifact candidate, not runtime verification.

### Phase D — artifact evidence

Record at minimum:

- source commit,
- build tool name and version when available,
- builder OS summary,
- image filename,
- image byte size,
- image SHA-256,
- build log path and SHA-256,
- manifest path,
- explicit negative claims for USB write and boot verification.

### Phase E — handoff to boot smoke test

A later boot smoke test must use the image hash from Phase D and record hardware evidence separately.

## Hard stops

Stop the build path if any of these occur:

- source commit differs from the authorized commit,
- build writes outside the declared output area,
- credential material appears in logs or manifests,
- DevBridge, MCP or inbound remote control is enabled,
- the process attempts media writing,
- the operator cannot capture image hash and build log hash.

## Required negative claims

Every real build receipt must state:

```json
{
  "usb_written": false,
  "hardware_booted": false,
  "runtime_verified": false,
  "devbridge_enabled": false,
  "mcp_enabled": false,
  "deployment_performed": false,
  "adr_accepted": false
}
```

## Promotion rule

Only an image with a recorded SHA-256 and build log can move to the USB boot smoke test queue.

A real image build does not authorize USB writing.
