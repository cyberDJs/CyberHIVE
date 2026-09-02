# Runbook — CyberHIVE Live USB Bootstrap

## Purpose

Guide the first CyberHIVE Live USB build, write, boot, and evidence capture cycle.

## Operator warning

The first live USB is experimental. Use non-critical hardware first. Do not test on machines containing irreplaceable data until the no-host-disk-write boundary has been independently verified.

## Build flow

1. Check out the repository.
2. Read `docs/work-blocks/WB-HIVE-BOOT-0001-live-usb-bootstrap.md`.
3. Read `infra/live-usb/safety-boundary.md`.
4. Build the candidate image from tracked configuration.
5. Generate SHA-256 and manifest.
6. Record build environment.

## USB write flow

1. Select an expendable USB drive.
2. Verify device path manually.
3. Write image using the documented tool.
4. Re-read device metadata where practical.
5. Label the USB with image version and date.

## First boot flow

1. Boot on a non-critical machine.
2. Select `offline-diagnostics` first.
3. Verify internal disks are not mounted read-write.
4. Run hardware inventory.
5. Export logs/evidence.
6. Reboot and select `controller-worker` only after the diagnostic boot passes.

## Evidence to capture

- image filename
- image SHA-256
- USB write tool and command
- test machine vendor/model
- CPU/RAM/GPU summary
- boot mode
- network status
- selected runtime mode
- health result
- inventory result
- disk mount state
- observed failures
- screenshots/photos where useful

## Stop conditions

Stop immediately if:

- an internal disk is mounted read-write without explicit operator action,
- DevBridge/MCP/SSH is exposed without local enablement,
- logs contain secret material,
- boot modifies firmware, boot entries, partitions or host OS state without explicit approval,
- the image attempts unapproved network tunneling.

## Recovery

For first tests:

- power off the test machine,
- remove USB,
- inspect host disk state from known-good OS if needed,
- preserve CyberHIVE evidence logs,
- mark the image unsafe until reviewed.
