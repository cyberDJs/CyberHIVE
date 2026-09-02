# Debian Live Candidate — Real Image Build Gate

## Status

Gate definition only in PR context. The PR validation workflow does not build an ISO.

## Candidate path

```text
infra/live-usb/debian-live
```

## Build wrapper

```text
infra/live-usb/debian-live/build-real-image.sh
```

The wrapper is intended for an explicitly authorized build-only execution.

## Approval token

Required environment value:

```text
CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB
```

The wrapper must refuse execution without that exact value before creating build output.

## Builder label

Required evidence label input:

```text
CYBERHIVE_REAL_IMAGE_BUILDER_LABEL=<safe-label>
```

Allowed characters:

```text
A-Z a-z 0-9 . _ : @ -
```

The wrapper must refuse unsafe labels before creating build output.

## Output directory

The canonical output directory is fixed:

```text
.cyberhive-live-real-build/
```

No output-directory override is supported by this gate.

## Tooling expectation

The first implementation expects a builder with `lb` available and one of these SHA-256 tools available:

```text
sha256sum
shasum
openssl
```

The wrapper does not install system packages. Builder provisioning is a separate operator concern.

## Build behavior

The wrapper may:

- copy the tracked Debian Live candidate to an output work directory,
- run the tracked live-build configuration,
- attempt the image build,
- copy a resulting image candidate to `.cyberhive-live-real-build/`,
- write manifest and hash evidence,
- write a failure manifest if no image is produced.

The wrapper must not:

- write USB or removable media,
- call disk formatting tools,
- mount or mutate host internal disks,
- claim boot or runtime verification,
- enable DevBridge/MCP,
- deploy anything.

## Manifest

The manifest must follow:

```text
infra/live-usb/debian-live/real-build-manifest.md
```

The final manifest hash must be external:

```text
<image-name>.manifest.json.sha256
```

Success evidence must fail closed when required SHA-256 evidence cannot be produced.

## Evidence boundary

A successful output means only:

```text
image artifact candidate exists
```

It does not mean:

```text
image boots
runtime works
networking works
internal disks are protected at runtime
USB media was written
ADR accepted
```

## Stop line

```text
ISO build: OPERATOR-AUTHORIZED ONLY
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```
