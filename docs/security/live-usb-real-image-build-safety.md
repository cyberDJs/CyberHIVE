# CyberHIVE Live USB Real Image Build Safety Boundary

## Boundary statement

`WB-HIVE-BOOT-0004` introduces a real image build gate, not a media write or runtime verification gate.

The only permitted artifact mutation is creation of build evidence inside the configured build output directory.

## Permitted by this gate

Permitted after explicit image-only approval:

- invoke tracked Debian Live image build tooling,
- create a candidate image artifact,
- create build logs,
- create SHA-256 sidecars,
- create a manifest using the existing real build manifest contract,
- publish or upload the evidence bundle in a later explicitly approved artifact workflow.

## Not permitted by this gate

This gate must not:

- write to USB or removable media,
- call `dd`, `mkfs`, `wipefs`, `parted` or equivalent disk mutation tools,
- format or repartition storage,
- mount host internal disks for mutation,
- perform hardware boot testing,
- claim runtime verification,
- enable DevBridge/MCP,
- deploy to production,
- embed credentials or enrollment secrets,
- accept ADR-0008.

## Approval token

The wrapper refuses to run unless this exact token is provided through the environment:

```text
CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB
```

The token is intentionally not a secret. It is a friction and audit marker proving that the operator requested image build only.

## Builder isolation

Preferred builder:

- disposable VM,
- ephemeral CI runner,
- container or microVM with no host disk mounts except the repository workspace and output directory.

Local builders are acceptable only when the operator understands that Live image builds may create many temporary files inside the workspace/output directory.

## Evidence classification

A successful build is evidence of image artifact creation only.

It is not evidence that:

- the image boots,
- the runtime works,
- internal disks are safe at runtime,
- networking works,
- hardware inventory is correct,
- DevBridge/MCP remain disabled after boot.

Those require separate boot smoke and runtime verification gates.

## Stop line

```text
ISO build: ALLOWED ONLY WITH EXPLICIT BUILD-ONLY TOKEN
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```
