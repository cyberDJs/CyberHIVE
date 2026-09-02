# CyberHIVE Live USB Real Build Safety Boundary

## Status

Planning boundary only. No image build, media write or runtime action is authorized here.

## Security objective

Move from repository dry-run to a future real image build without weakening the Live USB safety model.

The first real build must be treated as artifact creation only.

## Trust boundary

A future builder is not trusted with production credentials.

The build workspace must not contain:

- API credentials,
- SSH private keys,
- provider credentials,
- deployment credentials,
- enrollment credentials,
- production configuration secrets.

## Allowed in a later authorized build

A later authorized real build may:

- read tracked repository build inputs,
- use the selected live-image build toolchain,
- resolve declared operating-system package inputs,
- write an image artifact candidate to a declared output directory,
- write a build manifest,
- write build logs,
- compute hashes for the image, manifest and log.

## Forbidden in this work block

This work block must not:

- build an ISO,
- create a bootable image,
- write removable media,
- perform a hardware boot test,
- mount or modify host disks,
- enable SSH server exposure,
- enable MCP,
- enable DevBridge,
- create enrollment material,
- deploy any service,
- mark ADR-0007 accepted.

## Forbidden in a later build without a separate grant

A later image build grant still does not permit:

- USB/media writing,
- production deployment,
- live swarm enrollment,
- persistent overlay initialization with credentials,
- internal disk modification,
- privileged rescue operations,
- runtime verification claims.

## Evidence requirements

A future real build receipt must include:

- exact source commit,
- builder identity label,
- builder OS summary,
- build start and end timestamps,
- image filename and SHA-256,
- build log SHA-256,
- manifest SHA-256,
- package/rootfs evidence when available,
- explicit negative claims for USB write and boot/runtime verification.

## Failure handling

A failed build is still evidence.

Record:

- source commit,
- failure phase,
- relevant log excerpt or log hash,
- whether any image artifact was produced,
- whether any cleanup was manual,
- whether the builder workspace should be discarded.

## Promotion constraints

Only a successful artifact build with hashes may be handed to a separate USB boot smoke test.

Boot smoke testing must bind to the image SHA-256, not a filename alone.
