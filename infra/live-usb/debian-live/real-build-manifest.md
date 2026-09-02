# CyberHIVE Live USB Real Build Manifest Contract

## Purpose

A future real build manifest records image artifact creation evidence.

It is not a USB write report and not a boot verification report.

## Expected path

For a later real build:

```text
.cyberhive-live-real-build/<image-name>.manifest.json
```

## Manifest hash evidence

The final manifest SHA-256 must be recorded outside the manifest itself.

Recommended sidecar path:

```text
.cyberhive-live-real-build/<image-name>.manifest.json.sha256
```

The manifest must not contain a `manifest_sha256` field. Keeping the hash outside the manifest avoids a self-referential checksum.

## Required field schema

| Field | JSON type | Required | Notes |
|---|---:|---:|---|
| `schema` | string | yes | Must be `cyberhive.live.real_build.v0`. |
| `status` | string | yes | `ok` or `failed`. |
| `mode` | string | yes | Must be `real-build`. |
| `source_commit` | string | yes | Exact Git commit used for the build. |
| `candidate` | string | yes | Initial value: `debian-live`. |
| `candidate_path` | string | yes | Initial value: `infra/live-usb/debian-live`. |
| `builder_identity_label` | string | yes | Operator or runner label, not a secret. |
| `builder_os` | string | yes | Builder OS summary. |
| `build_tool` | string | yes | Selected live image build tool. |
| `build_tool_version` | string | yes | Version string or `UNKNOWN`. |
| `output_directory` | string | yes | Must stay inside `.cyberhive-live-real-build/`. |
| `image_filename` | string or null | yes | Null when no image exists. |
| `image_bytes` | integer or null | yes | Null when no image exists. |
| `image_sha256` | string or null | yes | Null when no image exists. |
| `build_log_filename` | string | yes | Build log evidence filename. |
| `build_log_sha256` | string | yes | SHA-256 of the build log. |
| `package_manifest_filename` | string | yes | Filename or `UNKNOWN`. |
| `package_manifest_sha256` | string | yes | SHA-256 or `UNKNOWN`. |
| `build_executed` | boolean | yes | True only when the build gate actually ran. |
| `image_created` | boolean | yes | True only when an image candidate exists and was hashed. |
| `usb_written` | boolean | yes | Must remain false for the build gate. |
| `hardware_booted` | boolean | yes | Must remain false until a separate boot smoke test. |
| `runtime_verified` | boolean | yes | Must remain false until independent runtime verification exists. |
| `devbridge_enabled` | boolean | yes | Must remain false for this build gate. |
| `mcp_enabled` | boolean | yes | Must remain false for this build gate. |
| `deployment_performed` | boolean | yes | Must remain false for this build gate. |
| `adr_accepted` | boolean | yes | Must remain false unless explicit project decision authority accepts the ADR. |

## Success manifest example

```json
{
  "schema": "cyberhive.live.real_build.v0",
  "status": "ok",
  "mode": "real-build",
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "candidate": "debian-live",
  "candidate_path": "infra/live-usb/debian-live",
  "builder_identity_label": "operator-or-runner-label",
  "builder_os": "Debian 12 amd64 disposable builder",
  "build_tool": "live-build",
  "build_tool_version": "UNKNOWN",
  "output_directory": ".cyberhive-live-real-build/",
  "image_filename": "cyberhive-live-usb-v0.1-amd64-20260902.iso",
  "image_bytes": 123456789,
  "image_sha256": "<sha256>",
  "build_log_filename": "cyberhive-live-usb-v0.1-amd64-20260902.build-log.txt",
  "build_log_sha256": "<sha256>",
  "package_manifest_filename": "cyberhive-live-usb-v0.1-amd64-20260902.packages.txt",
  "package_manifest_sha256": "<sha256>",
  "build_executed": true,
  "image_created": true,
  "usb_written": false,
  "hardware_booted": false,
  "runtime_verified": false,
  "devbridge_enabled": false,
  "mcp_enabled": false,
  "deployment_performed": false,
  "adr_accepted": false
}
```

## Failure manifest example

```json
{
  "schema": "cyberhive.live.real_build.v0",
  "status": "failed",
  "mode": "real-build",
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "candidate": "debian-live",
  "candidate_path": "infra/live-usb/debian-live",
  "builder_identity_label": "operator-or-runner-label",
  "builder_os": "Debian 12 amd64 disposable builder",
  "build_tool": "live-build",
  "build_tool_version": "UNKNOWN",
  "output_directory": ".cyberhive-live-real-build/",
  "image_filename": null,
  "image_bytes": null,
  "image_sha256": null,
  "build_log_filename": "cyberhive-live-usb-v0.1-amd64-20260902.build-log.txt",
  "build_log_sha256": "<sha256>",
  "package_manifest_filename": "UNKNOWN",
  "package_manifest_sha256": "UNKNOWN",
  "build_executed": true,
  "image_created": false,
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

## Manifest hash sidecar

The sidecar file records the SHA-256 of the final manifest bytes after the manifest has been written.

Recommended sidecar contents:

```text
<sha256>  <image-name>.manifest.json
```

## Failure manifest

Failed builds must still emit or record a manifest if possible.

If no image exists, `image_filename`, `image_bytes` and `image_sha256` must be null.

## Promotion rule

A future USB write gate may accept only a build manifest with:

- `status: ok`,
- `image_created: true`,
- non-empty `image_sha256`,
- external manifest hash sidecar exists,
- `usb_written: false`,
- `hardware_booted: false`,
- `runtime_verified: false`.
