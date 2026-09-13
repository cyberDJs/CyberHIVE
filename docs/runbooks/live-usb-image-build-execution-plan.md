# CyberHIVE Live USB Image Build Execution Plan Runbook

## Purpose

This runbook defines how to execute the first current-main CyberHIVE Live USB image build after the real image build gate exists on `main`.

This runbook is for planning and operator handoff. It does not execute the build by itself.

```text
IMAGE BUILD EXECUTION PLAN ONLY
```

## Preconditions

Before any execution, confirm and record:

- current `main` commit,
- whether the intended source commit is still the current `main`,
- post-merge CI state for that commit,
- runner type and builder label,
- operator approval for image build only,
- no project secrets required or exposed,
- no USB/media write authorization exists.

The current baseline for this plan was observed as:

```text
main_commit: c854089a375f3bd644d3445e45d7d119a4f4ba08
```

This value is a baseline, not a standing execution target. The main source commit must be re-read before execution.

## Primary path — GitHub manual workflow dispatch

Use this path for a current-main image artifact candidate.

1. Re-read `main` and record the exact source commit.
2. Confirm the target workflow is present:

   ```text
   .github/workflows/live-usb-real-image-build-manual.yml
   ```

3. Dispatch the workflow manually on `main` with build execution enabled.
4. Use a safe builder label that fits the `WB-HIVE-BOOT-0004` label policy.
5. Confirm the workflow provisions the bounded Debian container, Git, live-build tooling and SHA-256 tooling.
6. Confirm the uploaded evidence artifact name binds the source commit and workflow run.
7. Download or inspect the artifact evidence before any promotion decision.

Required workflow dispatch:

```text
workflow: Live USB real image build manual
ref: main
approval_token: BUILD_IMAGE_ONLY_NO_USB
run_build: true
builder_label: github-main-<sha>-run-<run_id> or another safe label
```

The dispatch must target the current `main` commit observed immediately before execution. A stale baseline commit is not a valid standing target.

The manual workflow dispatch is explicit image-only approval.

```text
manual workflow dispatch is explicit image-only approval
```

A successful workflow conclusion is not enough. The artifact contents must be inspected.

## Fallback path — disposable local builder

Use this only when GitHub Actions is unavailable or the operator intentionally chooses local build evidence.

Required command shape from repository root:

```sh
CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB \
CYBERHIVE_REAL_IMAGE_BUILDER_LABEL="operator-or-runner-label" \
sh infra/live-usb/debian-live/build-real-image.sh
```

The local builder must be disposable or isolated. Do not run this on a production host. Do not use a host that contains project secrets.

## Artifact evidence checklist

Capture the following before any next step:

| Field | Required |
|---|---:|
| repository | yes |
| branch/ref | yes |
| source commit | yes |
| workflow run or local receipt | yes |
| builder label | yes |
| build wrapper path | yes |
| image filename | when created |
| image SHA-256 | when created |
| manifest JSON | yes |
| manifest sidecar SHA-256 | yes |
| build log | yes |
| build log SHA-256 | yes |
| package/rootfs manifest | when available |
| known limitations | yes |

The exact source commit must match the workflow artifact manifest.

```text
exact source_commit must match the workflow artifact manifest
```

## Manifest inspection checklist

The manifest must state:

```json
{
  "usb_written": false,
  "hardware_booted": false,
  "runtime_verified": false,
  "deployment_performed": false,
  "adr_accepted": false
}
```

Reject promotion when:

- `source_commit` is `UNKNOWN`,
- `source_commit` does not match the intended source commit,
- image hash is missing for a created image,
- manifest hash sidecar is missing,
- build log is missing,
- manifest claims USB write, hardware boot, runtime verification, deployment or ADR acceptance.

## Promotion rule

After artifact inspection, the next work block should be a USB boot smoke plan or image artifact evidence registration, depending on evidence quality.

This runbook does not authorize the next work block.

## Explicit non-actions

This runbook does not authorize:

- USB/media writes,
- removable-media preparation,
- hardware boot testing,
- host disk mutation,
- runtime verification,
- DevBridge/MCP enablement,
- deployment,
- enrollment material creation,
- ADR acceptance.

## Stop line

```text
current-main image artifact: NOT CREATED BY THIS PLAN
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```
