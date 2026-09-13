# Debian Live Candidate — Real Build Plan

## Status

Plan implemented as a gate by `WB-HIVE-BOOT-0004`.

This file still does not run an image build. Image build execution is governed by the real image build gate wrapper and requires explicit image-only approval.

## Candidate path

```text
infra/live-usb/debian-live
```

## Build goal

Produce the first CyberHIVE Live USB image artifact candidate from the tracked Debian Live configuration.

The artifact candidate is intended for a later USB boot smoke test.

## Required input files

The build uses the existing tracked Debian Live candidate files:

- `auto/config`
- `config/package-lists/cyberhive-live.list.chroot`
- `config/includes.chroot/etc/cyberhive/live/config.env`
- `config/includes.chroot/usr/local/bin/cyberhive-live-health`
- `config/includes.chroot/usr/local/bin/cyberhive-role-selector`
- `config/includes.chroot/usr/local/bin/cyberhive-inventory`
- `config/includes.chroot/etc/systemd/system/cyberhive-live-agent.service`
- `config/includes.chroot/usr/lib/tmpfiles.d/cyberhive-live.conf`
- `config/hooks/live/001-cyberhive-live-skeleton.hook.chroot`

## Output directory

```text
.cyberhive-live-real-build/
```

The directory must stay ignored by Git.

## Build wrapper

```text
infra/live-usb/debian-live/build-real-image.sh
```

The wrapper requires:

```text
CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB
```

## Build artifact naming

Image name pattern:

```text
cyberhive-live-usb-v0.1-amd64-<YYYYMMDDTHHMMSSZ>.iso
```

Required sidecar files:

```text
cyberhive-live-usb-v0.1-amd64-<timestamp>.manifest.json
cyberhive-live-usb-v0.1-amd64-<timestamp>.manifest.json.sha256
cyberhive-live-usb-v0.1-amd64-<timestamp>.sha256
cyberhive-live-usb-v0.1-amd64-<timestamp>.build-log.txt
```

## Manifest contract

The real build manifest contract is defined in:

```text
infra/live-usb/debian-live/real-build-manifest.md
```

## Safety defaults to preserve

The image build must preserve:

- DevBridge disabled by default,
- MCP disabled by default,
- host disk writes disabled by default,
- no local discovery daemon in the v0.1 seed,
- no credentials embedded in the image,
- no runtime verification claim.

## Promotion rule

A build artifact candidate may move to boot smoke testing only after:

1. image SHA-256 exists,
2. manifest exists,
3. manifest SHA-256 sidecar exists,
4. build log exists,
5. source commit is recorded,
6. USB write remains explicitly false,
7. boot/runtime verification remains explicitly false.

## Non-goals

This gate does not include:

- USB writing,
- Secure Boot signing,
- hardware boot testing,
- persistent overlay activation,
- GPU inference,
- public federation,
- DevBridge/MCP runtime exposure,
- deployment,
- ADR acceptance.

## Stop line

```text
ISO build: NOT RUN BY PR
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```
