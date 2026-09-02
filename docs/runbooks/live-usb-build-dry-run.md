# CyberHIVE Live USB Build Dry-Run Runbook

## Scope

This runbook covers `WB-HIVE-BOOT-0002` only.

It verifies repository build inputs and produces a dry-run manifest. It does not build an image or test hardware.

## Preconditions

- Repository checkout is available.
- `WB-HIVE-BOOT-0001` Live USB skeleton is present.
- No secrets or local credentials are required.
- No removable media is required.
- No remote endpoint is required.

## Command

From repository root:

```sh
sh infra/live-usb/debian-live/build-dry-run.sh
```

Optional output override:

```sh
CYBERHIVE_LIVE_DRY_RUN_DIR=/tmp/cyberhive-live-dry-run sh infra/live-usb/debian-live/build-dry-run.sh
```

## Expected result

The command prints:

```text
CyberHIVE Live USB build dry-run passed
manifest: <path>
live_build_tool: available|missing
```

The manifest is written to:

```text
.cyberhive-live-build-dry-run/manifest.json
```

## Evidence to keep

For a local dry-run evidence note, record:

- repository URL,
- branch or commit,
- command used,
- dry-run manifest contents,
- whether `live_build_tool` was `available` or `missing`,
- any missing input path,
- any safety boundary failure.

## Failure handling

Stop and do not proceed to image build when:

- a required input path is missing,
- a local discovery daemon appears in the v0.1 seed,
- DevBridge/MCP disabled defaults are missing,
- host disk write disabled default is missing,
- the manifest cannot be written.

## Explicit non-results

A successful dry-run does not mean:

- an ISO was built,
- a USB drive was written,
- a host machine booted,
- disk safety was observed on hardware,
- a CyberHIVE runtime service is ready,
- DevBridge/MCP is usable.

## Next gate

The next work block may define a real local image build only after this dry-run has CI evidence and a review confirms that the dry-run did not widen the safety boundary.
