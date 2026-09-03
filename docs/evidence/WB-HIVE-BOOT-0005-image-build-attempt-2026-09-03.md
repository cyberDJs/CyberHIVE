# WB-HIVE-BOOT-0005 — v0.2 image build attempt evidence — 2026-09-03

## Authority

User approval was explicitly bound to:

- repository: `cyberDJs/CyberHIVE`
- PR: `#28`
- approved head: `8835c5af4861e0c37973719bd599519fc0ba9adf`
- scope: image build only

The approval did **not** authorize USB/media writes, hardware boot claims, deployment, merge, DevBridge/MCP enablement, remote-help enablement, or ADR acceptance.

## GitHub Actions execution

- workflow: `Live USB real image build gate`
- run ID: `33802441812`
- builder label: `github-pr-28-run-33802441812`
- exact-head checkout: PASS
- exact-head verification: PASS
- build-gate validation: PASS
- approved image-only build: FAIL
- failure evidence upload: PASS

## Failure result

The build produced no ISO. The preserved manifest reports:

```text
status: failed
live_version: 0.2.0-dev
source_commit: 8835c5af4861e0c37973719bd599519fc0ba9adf
image_created: false
usb_written: false
hardware_booted: false
runtime_verified: false
deployment_performed: false
adr_accepted: false
```

The preserved build log repeatedly showed:

```text
P: Executing auto/config script.
```

and terminated with:

```text
/usr/lib/live/build/config: 181: tr: Argument list too long
```

## Root cause

`infra/live-usb/debian-live/auto/config` called `lb config` without the live-build `noauto` sentinel. Because the invocation originated from the tracked `auto/config` hook, live-build re-entered `auto/config` recursively. The argument vector grew until the platform rejected it.

This was a build-bootstrap defect. There is no evidence that the SSH, browser-control, mDNS, host-disk guard, branding runtime, or support-bundle implementations were executed in the failed image build.

## Preserved failure artifact

- artifact ID: `9911596302`
- artifact name: `cyberhive-real-build-pr28-8835c5af4861e0c37973719bd599519fc0ba9adf-run33802441812`
- artifact ZIP SHA-256: `097c60c869a9cba726f75ef35ed38b99334081751b9de71b8a71ad52cd860108`
- build log SHA-256: `b0e388110b89d3061b83b6444265f579fe6c8baa5c52138e0ffa57b26e28feb2`
- preserved files: failed manifest, manifest SHA-256 sidecar, build log
- retention expiry reported by GitHub: 2026-10-03

## Repair

The bounded repair changes `auto/config` to invoke:

```sh
lb config noauto ...
```

and adds a regression guard to the Live Appliance v0.2 validator requiring the `noauto` form and rejecting the recursive form.

The repair changes the PR head, therefore the original image-build approval **cannot** be reused. A fresh explicit approval must bind to the repaired exact head after CI is green.

## Current boundary

```text
v0.2 image build: FAILED ON APPROVED HEAD
v0.2 repaired image build: NOT AUTHORIZED
USB/media write: NOT AUTHORIZED
v0.2 physical boot: NOT VERIFIED
deployment: NOT PERFORMED
merge: NOT AUTHORIZED
ADR-0009 accepted: NO
```
