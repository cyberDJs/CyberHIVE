# CyberHIVE Live USB Real Image Build Safety Boundary

## Boundary statement

`WB-HIVE-BOOT-0004` introduces a real image build gate, not a media write or runtime verification gate.

The only permitted artifact mutation is creation of build evidence inside the canonical build output directory.

```text
.cyberhive-live-real-build/
```

No output-directory override is permitted by this gate.

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

For the pre-merge GitHub path, applying the `approved:image-build-only` label is the
operator approval event. Only the `labeled` event may start that job. The job is limited
to same-repository pull requests, checks out the exact head SHA carried by the event,
uses read-only repository permissions and passes no repository secrets into the builder.
A subsequent `synchronize` event does not inherit authority from the existing label.

## Builder label safety

`CYBERHIVE_REAL_IMAGE_BUILDER_LABEL` must be non-secret evidence metadata.

The wrapper must accept only this safe character set:

```text
A-Z a-z 0-9 . _ : @ -
```

The wrapper must reject empty, overlong or unsafe labels before creating build output.

## Hash evidence safety

A real image build gate must fail closed when no SHA-256 tool is available.

Accepted SHA-256 tools:

```text
sha256sum
shasum
openssl
```

A successful build manifest must not use `UNKNOWN` for image SHA-256, build-log SHA-256 or manifest sidecar evidence.

## Builder isolation

Preferred builder:

- disposable VM,
- ephemeral CI runner,
- container or microVM with no host disk mounts except the repository workspace and canonical output directory.

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
