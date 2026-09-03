# WB-HIVE-BOOT-0004 — CyberHIVE Live USB Real Image Build Gate

## Status

Proposed implementation branch.

## Source of truth

- Repository: `cyberDJs/CyberHIVE`
- Base branch: `main`
- Parent gate: `WB-HIVE-BOOT-0003 — CyberHIVE Live USB Real Build Plan`

## Decision

Add the first governed real image build gate for the CyberHIVE Live USB candidate.

This work block creates the repository controls needed to build an ISO/image artifact only after an explicit build-only approval token is supplied by an operator.

## Scope

In scope:

- real image build wrapper for the Debian Live candidate,
- manual build gate documentation,
- manual workflow contract for later explicit image-build dispatch,
- validation workflow for this gate,
- artifact and manifest evidence requirements,
- security boundary checks that keep USB/media writes out of scope.

Out of scope:

- USB writing,
- hardware boot testing,
- runtime verification,
- deployment,
- DevBridge/MCP exposure,
- ADR acceptance.

## Authorization boundary

The repository change defines a gate. It does not itself run the image build.

A future build run requires the exact approval token:

```text
BUILD_IMAGE_ONLY_NO_USB
```

The build gate may create an ISO/image candidate and local evidence files. It must not write removable media and must not claim boot/runtime verification.

For an unmerged same-repository PR, the `approved:image-build-only` label is the
auditable approval event. It binds execution to the PR head SHA present in that label
event. A later push requires a fresh remove/re-apply cycle and therefore a fresh
approval event.

## Expected artifact directory

```text
.cyberhive-live-real-build/
```

The directory remains ignored by Git.

No output-directory override is supported by this gate. Artifact location and manifest evidence must stay aligned.

## Evidence bundle

A successful build gate run must produce or preserve:

- image artifact path,
- image SHA-256,
- image byte size,
- manifest JSON,
- manifest SHA-256 sidecar,
- build log,
- build log SHA-256,
- package/rootfs manifest when available,
- source commit,
- safe builder label and OS summary,
- explicit negative claims for USB write, boot, runtime verification, deployment and ADR acceptance.

## Required negative claims

```text
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```

## Acceptance criteria

- Gate files exist and are validated in CI.
- Real build wrapper requires the exact build-only token.
- Real build wrapper refuses to run without the token before creating output.
- Real build wrapper refuses unsafe builder labels before creating output.
- Build output remains inside `.cyberhive-live-real-build/`.
- No output-directory override exists for this gate.
- Build evidence fails closed when no SHA-256 tool exists.
- Success evidence cannot use `UNKNOWN` for image SHA-256, build-log SHA-256 or manifest sidecar hash.
- Build script contains no USB/media write command.
- Manifest contract from `WB-HIVE-BOOT-0003` is reused.
- CI validation does not run a real image build.
- Ordinary PR validation and synchronize events do not run a real image build.
- Only a same-repository `approved:image-build-only` label event may run the pre-merge build.
- The approved build checks out and verifies the exact PR head SHA from the label event.
- ADR-0008 remains proposed only.

## Stop line

```text
ISO build: NOT RUN BY PR
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
MCP/SSH/DevBridge exposure: NO
deploy: NO
ADR-0008 accepted: NO
```
