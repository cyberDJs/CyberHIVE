# CyberHIVE Live USB Build Dry-Run Safety Boundary

## Scope

This document defines the safety boundary for `WB-HIVE-BOOT-0002`.

The dry-run is a repository and CI preparation step. It is not a runtime, deployment, media write or hardware boot step.

## Allowed behavior

The dry-run wrapper may:

- check tracked repository paths,
- check disabled-by-default CyberHIVE safety flags,
- detect whether live-build tooling is visible,
- create a local dry-run output directory,
- write a dry-run manifest,
- run in GitHub Actions as an isolated CI job.

## Disallowed behavior

The dry-run wrapper must not:

- create an ISO image,
- write a removable device,
- mount or modify host disks,
- enable remote access,
- enable DevBridge or MCP,
- fetch code or binaries from the network,
- create enrollment credentials,
- claim runtime or boot verification.

## Required negative evidence

The dry-run manifest must keep these fields false:

```json
{
  "build_executed": false,
  "iso_created": false,
  "usb_written": false,
  "runtime_verified": false,
  "devbridge_enabled": false,
  "mcp_enabled": false,
  "host_disk_write_enabled": false
}
```

## Promotion gate

A future real build step must be a separate work block with its own review, evidence and rollback plan.
