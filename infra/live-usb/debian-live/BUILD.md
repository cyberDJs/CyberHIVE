# CyberHIVE Live USB Debian Live Build Dry-Run

## Status

`WB-HIVE-BOOT-0002` introduces a dry-run layer only.

It does not build an ISO image, write removable media, boot hardware, expose remote access, or verify runtime behavior.

## Goal

Prepare the first reviewable build path by checking repository inputs and producing a manifest that states exactly what was inspected and what was not done.

## Dry-run command

From the repository root:

```sh
sh infra/live-usb/debian-live/build-dry-run.sh
```

Expected local output directory:

```text
.cyberhive-live-build-dry-run/
```

Expected manifest path:

```text
.cyberhive-live-build-dry-run/manifest.json
```

## What the dry-run checks

- Debian Live candidate directory exists.
- `auto/config` exists.
- package seed exists.
- runtime defaults exist.
- health, role selector and inventory commands exist.
- tmpfiles policy exists.
- v0.1 does not include a local discovery daemon package.
- CyberHIVE safety defaults remain disabled-by-default.

## What the dry-run may report

- current source commit, when Git metadata is available,
- whether `lb` from live-build is visible on the machine,
- checked input path count,
- output manifest location.

`lb` visibility is informational only. This dry-run does not call live-build.

## What this does not prove

- no ISO image is built,
- no USB device is written,
- no boot target is tested,
- no runtime service is proven,
- no internal disk safety observation is collected,
- no DevBridge/MCP behavior is verified.

## Next gated steps

After this dry-run passes in CI, the next separate work block may define a real local image build. That future step must produce an image hash, build log, package manifest and explicit non-destructive hardware boot evidence before any runtime claim is accepted.
