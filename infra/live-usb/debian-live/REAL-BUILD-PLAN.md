# Debian Live Candidate — Real Build Plan

## Status

Plan only. No image build has been run by this file.

## Candidate path

```text
infra/live-usb/debian-live
```

## Build goal

Produce the first CyberHIVE Live USB image artifact candidate from the tracked Debian Live configuration.

The artifact candidate is intended for a later USB boot smoke test.

## Required input files

The future build uses the existing tracked Debian Live candidate files:

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

Proposed local output directory for a later build:

```text
.cyberhive-live-real-build/
```

The directory must stay ignored by Git.

## Build artifact naming

Proposed image name:

```text
cyberhive-live-usb-v0.1-amd64-<YYYYMMDD>.iso
```

Required sidecar files:

```text
cyberhive-live-usb-v0.1-amd64-<YYYYMMDD>.manifest.json
cyberhive-live-usb-v0.1-amd64-<YYYYMMDD>.sha256
cyberhive-live-usb-v0.1-amd64-<YYYYMMDD>.build-log.txt
```

## Manifest contract

The future real build manifest contract is defined in:

```text
infra/live-usb/debian-live/real-build-manifest.md
```

## Safety defaults to preserve

The future image build must preserve:

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
3. build log exists,
4. source commit is recorded,
5. USB write remains explicitly false,
6. boot/runtime verification remains explicitly false.

## Non-goals

This plan does not include:

- USB writing,
- Secure Boot signing,
- hardware boot testing,
- persistent overlay activation,
- GPU inference,
- public federation,
- DevBridge/MCP runtime exposure.
