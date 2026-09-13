# Debian Live Candidate — Image Build Execution Plan

## Status

Plan-only gate after `WB-HIVE-BOOT-0004`.

This document defines how the first current-main image artifact evidence should be produced after the real image build gate has merged.

It does not execute a build.

```text
IMAGE BUILD EXECUTION PLAN ONLY
```

## Candidate path

```text
infra/live-usb/debian-live
```

## Existing build mechanism

Use the existing image-only wrapper:

```text
infra/live-usb/debian-live/build-real-image.sh
```

Use the existing evidence directory:

```text
.cyberhive-live-real-build/
```

## Execution authority

A merge to `main` does not automatically authorize an image build.

Valid image-only execution authority must be explicit:

- GitHub manual workflow dispatch on `main`, or
- local disposable builder with `CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB`.

The manual workflow dispatch is explicit image-only approval.

## Source commit boundary

The main source commit must be re-read before execution.

The build evidence must record the exact source commit and the exact source_commit must match the workflow artifact manifest.

If source commit cannot be resolved, success evidence is invalid.

## Expected execution result

A successful image execution may create:

```text
image artifact candidate exists
```

It does not create:

```text
boot evidence
runtime verification
USB write evidence
deployment evidence
ADR acceptance
```

## Required artifact evidence

Minimum evidence bundle:

- source commit,
- builder label,
- workflow run ID or local receipt ID,
- image filename when created,
- image SHA-256 when created,
- manifest JSON,
- manifest sidecar SHA-256,
- build log,
- build log SHA-256,
- package/rootfs manifest when available,
- known limitations.

## Required negative claims

```text
current-main image artifact: NOT CREATED BY THIS PLAN
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```

## Promotion hold

Do not proceed to USB boot smoke from workflow success alone.

Promotion requires inspected artifact evidence and a separate work block.

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
