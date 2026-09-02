# CyberHIVE Live USB Real Build Manifest Contract

## Purpose

A future real build manifest records image artifact creation evidence.

It is not a USB write report and not a boot verification report.

## Expected path

For a later real build:

```text
.cyberhive-live-real-build/<image-name>.manifest.json
```

## Required fields

```json
{
  "schema": "cyberhive.live.real_build.v0",
  "status": "ok|failed",
  "mode": "real-build",
  "source_commit": "<git commit>",
  "candidate": "debian-live",
  "candidate_path": "infra/live-usb/debian-live",
  "builder_identity_label": "<operator or runner label>",
  "builder_os": "<summary>",
  "build_tool": "<tool name>",
  "build_tool_version": "<version or UNKNOWN>",
  "output_directory": ".cyberhive-live-real-build/",
  "image_filename": "<filename or null>",
  "image_bytes": "<integer or null>",
  "image_sha256": "<hash or null>",
  "manifest_sha256": "<hash of final manifest or null>",
  "build_log_filename": "<filename>",
  "build_log_sha256": "<hash>",
  "package_manifest_filename": "<filename or UNKNOWN>",
  "package_manifest_sha256": "<hash or UNKNOWN>",
  "build_executed": true,
  "image_created": "true|false",
  "usb_written": false,
  "hardware_booted": false,
  "runtime_verified": false,
  "devbridge_enabled": false,
  "mcp_enabled": false,
  "deployment_performed": false,
  "adr_accepted": false
}
```

## Semantics

- `build_executed: true` means the image build gate actually ran.
- `image_created: true` means an image artifact candidate exists and was hashed.
- `usb_written: false` must remain false for the build gate.
- `hardware_booted: false` must remain false until a separate boot smoke test.
- `runtime_verified: false` must remain false until independent runtime verification exists.
- `adr_accepted: false` must remain false unless explicit project decision authority accepts the ADR.

## Failure manifest

Failed builds must still emit or record a manifest if possible.

If no image exists, `image_filename`, `image_bytes` and `image_sha256` must be null.

## Promotion rule

A future USB write gate may accept only a build manifest with:

- `status: ok`,
- `image_created: true`,
- non-empty `image_sha256`,
- `usb_written: false`,
- `hardware_booted: false`,
- `runtime_verified: false`.
