# CyberHIVE Live USB Image Build Execution Safety

## Scope

This document defines the safety boundary for `WB-HIVE-BOOT-0005`.

The work block is a plan for image build execution evidence. It does not execute the build and does not change the runtime or hardware state.

```text
IMAGE BUILD EXECUTION PLAN ONLY
```

## Threat model

Relevant risks:

- stale source commit used for artifact evidence,
- workflow result mistaken for artifact verification,
- image artifact mistaken for boot/runtime verification,
- stale PR label authority reused after a push,
- build runner leaking project secrets,
- build container given broader privileges than required,
- artifact bundle missing manifest or hash sidecars,
- uninspected artifact promoted to USB boot smoke,
- ADR-0008 treated as accepted because gate code exists.

## Controls

### Source binding

The main source commit must be re-read before execution.

The evidence artifact must bind to the exact source commit used by the build. `UNKNOWN` is not acceptable for success evidence.

### Approval boundary

Manual workflow dispatch is explicit image-only approval.

Local execution requires the exact build-only approval token:

```text
CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB
```

No approval event in this work block authorizes USB/media writes, boot tests, runtime verification or deployment.

### Runner boundary

Preferred runner:

```text
GitHub-hosted ephemeral runner with bounded Debian container
```

Fallback runner:

```text
disposable local builder
```

Do not use a production host or a host containing project secrets as the builder.

### Evidence boundary

Workflow success means only that the workflow concluded successfully. It is not image verification by itself.

Artifact evidence must be inspected before promotion:

- manifest JSON,
- source commit,
- image hash when present,
- manifest sidecar hash,
- build log,
- negative claims.

The exact source_commit must match the workflow artifact manifest.

### Promotion boundary

A successful image artifact candidate may only be promoted to a future USB boot smoke work block after evidence inspection.

This work block cannot promote to USB write, boot smoke or runtime verification.

## Required negative claims

```text
current-main image artifact: NOT CREATED BY THIS PLAN
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```

## ADR state

`ADR-0008` remains proposed unless a separate authority event accepts it.

File existence, code merge and passing CI are not ADR acceptance.

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
