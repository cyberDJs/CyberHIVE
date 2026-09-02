# ADR-0008 — CyberHIVE Live USB Real Image Build Gate

## Status

Proposed

This ADR is a candidate only. File existence is not acceptance.

## Context

`WB-HIVE-BOOT-0003` defined the real build plan and manifest contract without executing a build.

The next step is to introduce a controlled gate that can create a real ISO/image candidate while preserving the separation between image creation, USB writing, boot smoke testing, runtime verification and deployment.

## Decision

Introduce a build-only gate for the Debian Live candidate.

The gate requires an explicit environment approval token and produces image/build evidence only. It does not authorize media writes, hardware boot tests, runtime verification, deployment, DevBridge/MCP exposure or ADR acceptance.

The gate uses a fixed canonical output directory:

```text
.cyberhive-live-real-build/
```

No output-directory override is part of this gate.

## Consequences

Positive:

- The project gets a concrete path from repository skeleton to first image artifact.
- Image artifact evidence becomes manifest-driven and hashable.
- Artifact location and manifest evidence stay aligned through one canonical output directory.
- USB write and boot smoke remain independent gates.
- Failed builds can still produce useful failure manifests and logs.

Negative:

- Live image builds are slower and more resource intensive than dry-runs.
- The current Debian Live skeleton may expose build-tooling issues that were intentionally not exercised by prior gates.
- Build output can be large and must remain outside Git.

## Security boundary

The build gate must not include commands that mutate disks or write removable media.

Explicitly out of scope:

- `dd`,
- `mkfs`,
- `wipefs`,
- `parted`,
- USB/media writing,
- boot testing,
- runtime verification,
- credential or enrollment secret embedding,
- DevBridge/MCP exposure,
- deployment.

## Evidence boundary

The build gate must fail closed when SHA-256 evidence cannot be produced.

The build gate must reject unsafe builder labels before creating output. Builder labels are evidence metadata, not secrets.

## Verification

Before acceptance, the project needs:

- PR review of the build gate files,
- CI validation of the gate boundaries,
- no-token refusal evidence from the validator,
- unsafe-label refusal evidence from the validator,
- one explicit image-only build attempt receipt,
- manifest and sidecar hash evidence,
- confirmation that no USB/boot/runtime/deploy claims were made by the build gate.

## Rollback

Remove the manual build workflow, build wrapper, runbook and work block. Keep prior dry-run and real build plan gates intact.

## ADR required

Yes, if this gate becomes the durable public build boundary.

## Current authority state

```text
ADR accepted: NO
```
