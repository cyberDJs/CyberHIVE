# ADR-0026 — CyberHIVE unattended single-USB A/B OTA

Proposed

## Context

CyberHIVE v0.2 proved physical boot, local control plane, SSH bootstrap repair, web service, mDNS and host-disk guard behavior, but its live overlay and Tailscale bootstrap are ephemeral. The target development node must remain reachable after the operator leaves and must accept future runtime updates without rewriting the only USB from another computer.

## Decision

Use one removable USB with two trust/storage layers:

1. a small stable UEFI partition labeled `CYBERHIVE_EFI`, containing a standalone GRUB loader and a writable GRUB environment block;
2. two ext4 runtime partitions labeled `CYBERHIVE_A` and `CYBERHIVE_B`, plus a separate ext4 `CYBERHIVE_STATE` partition for persistent operator/device state.

GRUB is not replaced by ordinary OTA. It boots one slot by `live-media-path`. OTA downloads a signed slot bundle into the inactive slot, verifies signature, bytes and SHA-256, and marks it pending. The bootloader gives the pending slot one attempt. Userspace health commits it; otherwise a reboot returns to the previous slot.

Persistent state is allowlisted rather than persisting the full root filesystem: NetworkManager Wi-Fi profiles, Tailscale state, SSH host identity, operator authorized keys, OTA state and bounded evidence.

## Security boundary

Management TCP ports 22 and 80 are dropped on interfaces other than `tailscale0`. OTA trust uses OpenSSH SSHSIG verification with a dedicated release public key. The corresponding private signing key is not stored in the repository or appliance.

The updater verifies that `CYBERHIVE_EFI`, `CYBERHIVE_A`, `CYBERHIVE_B` and `CYBERHIVE_STATE` have the same parent disk and that the parent transport is USB before changing slot or boot state. It does not perform partitioning or raw-device writes at runtime.

## Consequences

The node can be left unattended after one local Wi-Fi/Tailscale enrollment. Future normal runtime releases can be installed remotely even with only one physical USB. Bootloader-format changes still require a separate maintenance path and stronger authorization. Physical media failure remains outside A/B rollback coverage.
