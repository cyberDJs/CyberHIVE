---
id: WB-HIVE-BOOT-0003
type: work-block
title: CyberHIVE Live USB Real Build Plan
status: proposed
owner: CyberHIVE
created: 2026-09-02
updated: 2026-09-02
scope: repository-only real build planning
depends_on:
  - WB-HIVE-BOOT-0001
  - WB-HIVE-BOOT-0002
---

# WB-HIVE-BOOT-0003 — CyberHIVE Live USB Real Build Plan

## Problem

`WB-HIVE-BOOT-0001` created the Live USB skeleton and `WB-HIVE-BOOT-0002` added a repository-only build dry-run gate.

The next step is to define the first real image-build gate without performing the build, creating an ISO, writing media or claiming runtime verification.

## Intent

Create a governed plan for the first real CyberHIVE Live USB image build.

The plan must define:

1. what is allowed during a future real build,
2. what remains outside scope,
3. the build evidence bundle,
4. the artifact naming and hash rules,
5. the operator approval boundary,
6. the promotion path from image build to USB boot smoke test.

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
- ADR acceptance,
- production runtime verification.

## Scope

Repository changes expected in this block:

- real build plan runbook,
- real build safety boundary,
- proposed ADR candidate for build gating,
- real build manifest contract,
- build-plan documentation update,
- validation workflow that checks the plan only.

## Primary design

Use a staged build gate:

```text
Plan only -> explicitly authorized local image build -> artifact evidence -> separate USB boot smoke test
```

The real build is allowed only in a later work block with explicit build authorization bound to the source commit and build directory.

USB writing is a separate later authorization. A successful image build is not boot verification.

## Evidence vocabulary

Allowed evidence terms for this block:

- `PROPOSED` for the plan,
- `SIMULATED` for validation-only CI checks,
- `UNKNOWN` for runtime outcomes.

Forbidden evidence terms for this block:

- `VERIFIED` runtime,
- `booted`,
- `USB written`,
- `deploy complete`,
- `ADR accepted`.

## Verification

Acceptable verification for this block:

- required plan files exist,
- shell syntax of the validator passes,
- plan files contain the mandatory negative claims,
- the validation workflow completes,
- no image/media/runtime claim is made.

Not acceptable as verification for this block:

- saying the image builds,
- saying a USB boots,
- saying internal disk safety was observed on hardware,
- saying ADR-0007 is accepted.

## Rollback

Repository rollback is removal or supersession of the plan files, validator, workflow and documentation changes.

Runtime rollback is not applicable because this work block must not create runtime state.

## ADR required

Candidate only, not accepted. This block introduces proposed `ADR-0007 — Live USB Real Build Gate` as a decision candidate for the real image-build boundary.

Acceptance requires explicit project decision authority.
