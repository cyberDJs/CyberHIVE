# WB-HIVE-BOOT-0002 Source Map

## Canonical repository

`cyberDJs/CyberHIVE`

## Base state

This work starts after PR #23 merged `WB-HIVE-BOOT-0001` into `main`.

## Primary files

- `docs/work-blocks/WB-HIVE-BOOT-0002-build-dry-run.md`
- `docs/runbooks/live-usb-build-dry-run.md`
- `docs/security/live-usb-build-dry-run-safety.md`
- `docs/adr/ADR-0006-live-usb-build-dry-run-boundary.md`
- `infra/live-usb/debian-live/BUILD.md`
- `infra/live-usb/debian-live/build-dry-run.sh`
- `infra/live-usb/debian-live/expected-manifest.md`
- `scripts/validate-live-usb-build-dry-run.sh`
- `.github/workflows/live-usb-build-dry-run.yml`

## Verification state

Repository/CI dry-run only. No ISO build, USB write, hardware boot, runtime verification, DevBridge/MCP enablement or deployment.
