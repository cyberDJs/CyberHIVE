---
id: WB-HIVE-BOOT-0002
type: work-block
title: CyberHIVE Live USB Build Dry-Run
status: proposed
owner: CyberHIVE
created: 2026-09-02
updated: 2026-09-02
scope: repository-only dry-run
depends_on:
  - WB-HIVE-BOOT-0001
---

# WB-HIVE-BOOT-0002 — CyberHIVE Live USB Build Dry-Run

## Problem

`WB-HIVE-BOOT-0001` established the CyberHIVE Live USB repository skeleton. The next step must prove that the tracked build inputs are coherent enough to prepare for an image build without claiming that an image exists, that a USB was written, or that hardware booted.

## Intent

Add a conservative build dry-run layer for the Debian Live candidate.

The dry-run must:

1. inspect tracked Live USB build inputs,
2. verify the expected file layout,
3. preserve the safety defaults from the skeleton,
4. emit a reviewable manifest,
5. run safely in CI without producing an ISO image,
6. keep future real image build, USB write and boot verification as separate governed steps.

## Boundary

This work block does not authorize or perform:

- ISO image creation,
- USB media writing,
- hardware boot testing,
- host disk mutation,
- privileged host operations,
- remote access exposure,
- DevBridge or MCP enablement,
- deployment,
- enrollment material creation,
- production runtime verification.

## Scope

Repository changes expected in this block:

- build dry-run runbook,
- dry-run wrapper script,
- expected manifest contract,
- dry-run validator,
- CI workflow that runs only the validator and dry-run wrapper,
- build-plan documentation update.

## Primary design

Use a POSIX shell wrapper as the first dry-run surface:

```text
infra/live-usb/debian-live/build-dry-run.sh
```

The wrapper must not build an image. It checks that the existing Debian Live candidate inputs are present, confirms the v0.1 safety boundary, detects whether live-build tooling is available, and writes a manifest under a local ephemeral dry-run output directory.

## Output manifest

The dry-run manifest is a claim/evidence candidate, not product verification.

Required facts:

- schema identifier,
- dry-run mode,
- source commit when Git metadata is available,
- build candidate path,
- whether live-build tooling is visible,
- checked input paths,
- explicit `build_executed: false`,
- explicit `iso_created: false`,
- explicit `usb_written: false`,
- explicit `runtime_verified: false`.

## Security posture

The dry-run must preserve CyberHIVE defaults:

- no credentials in repository files,
- no local discovery daemon in v0.1 seed,
- DevBridge/MCP disabled by default,
- host disk writes disabled by default,
- no automatic inbound remote control,
- no public exposure.

## Verification

Acceptable verification for this block:

- shell syntax checks pass,
- required files exist,
- obvious credential patterns are absent from the tracked dry-run scope,
- blocked build/media/host-control commands are absent from the dry-run wrapper,
- CI dry-run job completes and prints a dry-run manifest.

Not acceptable as verification for this block:

- saying the image builds,
- saying the USB boots,
- saying runtime behavior is verified,
- saying internal disk safety has been observed on hardware.

## Rollback

Repository rollback is removal or supersession of the dry-run wrapper, validator, workflow and documentation.

Runtime rollback is not applicable because this work block must not create runtime state outside ephemeral CI/local dry-run output.

## ADR required

No. This block implements the already selected conservative build-preparation path. A future ADR is required if the project commits to a final base image strategy, persistent overlay policy, Secure Boot policy, or DevBridge/MCP runtime boundary.
