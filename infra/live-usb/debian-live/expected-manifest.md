# CyberHIVE Live USB Build Dry-Run Manifest Contract

## Purpose

The build dry-run manifest records repository input checks for the first Live USB image path.

It is not an ISO manifest and not a boot verification report.

## Expected path

```text
.cyberhive-live-build-dry-run/manifest.json
```

## Required fields

```json
{
  "schema": "cyberhive.live.build_dry_run.v0",
  "status": "ok",
  "mode": "dry-run",
  "source_commit": "<git commit or UNKNOWN>",
  "candidate": "debian-live",
  "candidate_path": "infra/live-usb/debian-live",
  "live_build_tool": "available|missing",
  "checked_paths": 9,
  "build_executed": false,
  "iso_created": false,
  "usb_written": false,
  "runtime_verified": false,
  "devbridge_enabled": false,
  "mcp_enabled": false,
  "host_disk_write_enabled": false
}
```

## Semantics

- `live_build_tool: available` means the builder command is visible on the local system. It does not mean it was executed.
- `checked_paths` is the count of required tracked Debian Live candidate inputs checked by the wrapper.
- `build_executed: false` must remain false for this work block.
- `iso_created: false` must remain false for this work block.
- `usb_written: false` must remain false for this work block.
- `runtime_verified: false` must remain false until a separate boot smoke test produces evidence.

## Promotion rule

A future real image build must use a different schema and must include image filename, image hash, package/rootfs manifest, builder environment and explicit build log reference.
