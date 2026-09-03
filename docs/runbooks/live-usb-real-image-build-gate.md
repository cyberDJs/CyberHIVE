# CyberHIVE Live USB Real Image Build Gate Runbook

## Purpose

This runbook defines how to run the first real image build gate for the CyberHIVE Live USB candidate.

This is an image artifact gate only. It is not a USB write, not a boot test and not runtime verification.

## Preconditions

Required:

- clean checkout of the target source commit,
- disposable local builder or isolated CI runner,
- Debian Live build tooling available as `lb`,
- a SHA-256 tool available as `sha256sum`, `shasum` or `openssl`,
- enough disk space for a Live ISO build,
- no project secrets in the builder environment,
- explicit operator approval for image build only.

The GitHub-hosted manual workflow provisions these prerequisites inside an
ephemeral Debian Bookworm container with only the mount capability required by
live-build. The container mounts only the checked-out repository workspace and
is discarded after the build. Artifact upload excludes the temporary rootfs.

Approval token:

```text
BUILD_IMAGE_ONLY_NO_USB
```

## Builder label policy

`CYBERHIVE_REAL_IMAGE_BUILDER_LABEL` is evidence metadata, not a secret.

Allowed characters:

```text
A-Z a-z 0-9 . _ : @ -
```

Length:

```text
1-80 characters
```

The wrapper must refuse unsafe labels before creating build output.

## Command

From repository root:

```sh
CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB \
CYBERHIVE_REAL_IMAGE_BUILDER_LABEL="operator-or-runner-label" \
sh infra/live-usb/debian-live/build-real-image.sh
```

## Output directory policy

The build output directory is fixed:

```text
.cyberhive-live-real-build/
```

No output-directory override is supported by this gate. This keeps artifact location and manifest evidence aligned.

## Expected outputs

Expected evidence files:

```text
<image-name>.iso
<image-name>.sha256
<image-name>.manifest.json
<image-name>.manifest.json.sha256
<image-name>.build-log.txt
<image-name>.packages.txt or UNKNOWN in manifest
```

Failed builds must still leave a manifest and build log when possible.

## Required checks after build

Confirm:

- manifest `status` is `ok` or `failed`,
- `build_executed` is `true`,
- `usb_written` is `false`,
- `hardware_booted` is `false`,
- `runtime_verified` is `false`,
- `deployment_performed` is `false`,
- `adr_accepted` is `false`,
- manifest hash is in the external `.manifest.json.sha256` sidecar,
- image hash exists only when `image_created` is `true`,
- success manifest does not contain `UNKNOWN` for image SHA-256, build-log SHA-256 or manifest sidecar hash.

## Promotion to boot smoke

Promotion to a future boot smoke test requires:

- successful image build manifest,
- image SHA-256,
- manifest sidecar SHA-256,
- build log SHA-256,
- source commit,
- no USB write claim from this gate,
- no boot/runtime verification claim from this gate.

## Explicit non-actions

This runbook does not authorize:

- `dd`,
- disk formatting,
- partitioning,
- writing removable media,
- booting hardware,
- mounting host internal disks,
- deployment,
- DevBridge/MCP enablement,
- ADR acceptance.

## Stop line

```text
ISO build: OPERATOR-AUTHORIZED ONLY
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```
