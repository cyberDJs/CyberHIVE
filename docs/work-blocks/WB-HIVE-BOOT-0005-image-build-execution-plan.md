# WB-HIVE-BOOT-0005 — CyberHIVE Live USB Image Build Execution Plan

## Status

Proposed / plan-only.

This work block defines the execution plan for producing the first current-main CyberHIVE Live USB image artifact evidence after `WB-HIVE-BOOT-0004` merged the real image build gate.

It does not build an image, write USB media, boot hardware, verify runtime behavior, deploy anything or accept ADR-0008.

## Baseline

Observed source baseline for this plan:

```text
repository: cyberDJs/CyberHIVE
branch: main
main_commit: c854089a375f3bd644d3445e45d7d119a4f4ba08
source_of_main_commit: PR #27 merge
```

The source baseline must be re-read before any image build execution. If `main` has moved, this work block is still a plan, but the execution evidence must bind to the newly observed source commit.

## Decision

Use the existing `WB-HIVE-BOOT-0004` real image build gate as the only approved image-build mechanism for the next step.

Primary execution path:

```text
GitHub Actions manual workflow dispatch on main
```

Fallback execution path:

```text
Disposable local builder running infra/live-usb/debian-live/build-real-image.sh
```

Both paths are image-build-only. Neither path authorizes USB/media writes, hardware boot, runtime verification, deployment, DevBridge/MCP enablement, enrollment material creation or ADR acceptance.

## Scope

In scope for this work block:

- current-main image build execution plan,
- exact source commit binding requirements,
- approval boundary for image-only execution,
- evidence capture checklist,
- artifact inspection checklist,
- promotion gate into a future USB boot smoke work block,
- validation workflow for this plan.

Out of scope for this work block:

- running the image build,
- creating a current-main image artifact,
- downloading or inspecting image artifacts,
- writing any removable media,
- booting hardware,
- runtime verification,
- deployment,
- accepting ADR-0008.

## Operation classes

This pull request:

```text
operation_class: REPO_WRITE
scope: documentation and validation workflow only
```

Future workflow dispatch:

```text
operation_class: REMOTE_WRITE + COMPUTE
scope: manual GitHub workflow dispatch on main
```

Future build execution:

```text
operation_class: COMPUTE
scope: isolated GitHub-hosted runner or disposable local builder
```

Future USB write or boot smoke:

```text
operation_class: OUT_OF_SCOPE_FOR_WB-HIVE-BOOT-0005
```

## Execution phases

### Phase 0 — Re-read canonical source

Before any build execution, record:

```text
main source commit must be re-read before execution
```

Minimum fields:

- repository,
- branch,
- current `main` commit,
- tree SHA when available,
- whether post-merge validation is green for that commit,
- whether the build is being run from the exact same commit.

### Phase 1 — Explicit build-only approval

A merge is not image-build authority.

Valid image-only approval events:

1. GitHub manual workflow dispatch with an explicit build input enabled.
2. Local operator command with `CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB`.
3. For an unmerged same-repository PR only, the `approved:image-build-only` label event defined by `WB-HIVE-BOOT-0004`.

Manual GitHub workflow dispatch is classified as `REMOTE_WRITE + COMPUTE`: it mutates GitHub Actions state by starting a remote workflow run, and the workflow then performs an isolated compute build when explicitly enabled.

The approval must bind:

- source commit,
- build-only scope,
- no USB/media write,
- no boot claim,
- no runtime claim,
- runner label,
- artifact retention location.

### Phase 2 — Image-only build execution

Use the tracked wrapper:

```text
infra/live-usb/debian-live/build-real-image.sh
```

The wrapper is expected to refuse execution without the exact build-only token and to fail closed when source commit or SHA-256 evidence cannot be resolved.

### Phase 3 — Evidence capture

The evidence bundle must include:

- source commit,
- builder label,
- run ID or local receipt ID,
- build command or workflow path,
- image artifact filename when created,
- image SHA-256 when image exists,
- manifest JSON,
- manifest sidecar SHA-256,
- build log,
- build log SHA-256,
- package/rootfs manifest when available,
- negative claims for USB, boot, runtime, deployment and ADR.

The exact source commit in the evidence must match the built artifact manifest.

```text
exact source_commit must match the workflow artifact manifest
```

### Phase 4 — Evidence inspection

Before promotion, inspect the artifact evidence, not just the workflow conclusion.

Minimum inspection:

- artifact exists,
- artifact name binds source commit or run ID,
- manifest parses as JSON,
- `source_commit` is exact and not `UNKNOWN`,
- image hash sidecar exists when `image_created` is true,
- manifest sidecar hash exists,
- negative claims remain false for USB, boot, runtime, deployment and ADR,
- build log exists.

### Phase 5 — Hold before boot smoke

This work block must stop after image evidence planning.

Promotion to USB boot smoke requires a separate work block with explicit authorization and hardware evidence requirements.

## Acceptance criteria

This work block is complete when:

- this work-block document exists,
- the execution-plan runbook exists,
- the safety document exists,
- the source map exists,
- the Debian Live execution-plan document exists,
- the build plan references `WB-HIVE-BOOT-0005`,
- the validation workflow for this plan is present,
- the validation script passes in CI,
- no image build was run by this work block,
- no current-main image artifact is claimed by this work block.

## Required boundary markers

```text
IMAGE BUILD EXECUTION PLAN ONLY
current-main image artifact: NOT CREATED BY THIS PLAN
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```

## Stop line

```text
image build execution: PLAN ONLY
current-main image artifact: NOT CREATED BY THIS PLAN
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```
