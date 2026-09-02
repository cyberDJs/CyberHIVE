# ADR-0006 — Live USB Build Dry-Run Boundary

## Status

Proposed

## Context

CyberHIVE needs a path from repository skeleton toward a bootable Live USB image without prematurely claiming runtime verification or widening the safety boundary.

`WB-HIVE-BOOT-0002` introduces a dry-run layer that validates tracked build inputs and emits a manifest, while keeping real image build and hardware boot testing as separate governed steps.

## Decision

The first Live USB build preparation step is a dry-run wrapper, not an image builder.

The dry-run wrapper may inspect repository files, check safety defaults, detect local build-tool availability and write a dry-run manifest.

The dry-run wrapper must not create an ISO, write media, modify host disks, expose remote access, enable DevBridge/MCP, fetch remote code, create enrollment material or claim runtime verification.

## Consequences

Positive:

- safer transition from docs skeleton to build work,
- CI can validate repository coherence without producing binary artifacts,
- evidence vocabulary stays explicit,
- future build and boot verification gates remain separate.

Tradeoffs:

- no immediate bootable image from this step,
- one additional PR before real local image build,
- manifest is a preparation receipt only.

## Verification

- required dry-run files exist,
- shell syntax passes,
- blocked commands are absent from the dry-run wrapper,
- manifest fields explicitly mark build/image/media/runtime outcomes as false,
- CI dry-run job completes.

## Notes

This ADR remains proposed until explicitly accepted by project decision authority. The implementation may reference it, but the file existing in the repository is not itself acceptance.
