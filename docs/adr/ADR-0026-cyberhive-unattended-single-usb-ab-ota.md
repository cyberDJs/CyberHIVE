# ADR-0026 - CyberHIVE unattended single-USB A/B OTA

Status: Proposed
Date: 2026-09-04

## Context

CyberHIVE v0.2 proved physical boot, local control plane, SSH bootstrap repair, web service, mDNS and host-disk guard behavior, but its live overlay and Tailscale bootstrap are ephemeral. The target development node must remain reachable after the operator leaves and must accept future runtime updates without rewriting the only USB from another computer.

Fresh review of the v0.3 implementation identified crash-consistency and unattended-recovery gaps: pending OTA metadata could lag the bootloader, commit state crossed STATE and EFI without a recovery transaction, failed releases could be retried forever, and a USB device reporting `RM=0` could be misclassified as an internal disk.

## Decision

Use one removable USB with two trust/storage layers:

1. a small stable UEFI partition labeled `CYBER_EFI`, containing a standalone GRUB loader and a writable GRUB environment block;
2. two ext4 runtime partitions labeled `CYBERHIVE_A` and `CYBERHIVE_B`, plus a separate ext4 `CYBERHIVE_STATE` partition for persistent operator/device state.

GRUB is not replaced by ordinary OTA. It loads the kernel and initrd from the slot on the firmware-selected EFI parent and passes live-boot both the selected slot filesystem UUID and `live-media-path`. OTA downloads a signed slot bundle into the inactive slot, verifies signature, bytes and SHA-256, and marks it pending. The bootloader gives the pending slot one attempt. Userspace health commits it; otherwise a reboot returns to the previous slot.

`CYBERHIVE_STATE` is the durable transaction journal. The updater persists and syncs complete pending metadata before arming GRUB. A healthy candidate writes a recoverable commit transaction and advances anti-downgrade state before clearing pending boot state in EFI. On the next boot, an interrupted cross-filesystem commit is either finalized on the candidate slot or restored to the previous release state after rollback.

A failed or rolled-back release is quarantined by release ID and sequence. The periodic updater refuses that release and requires a newer sequence, preventing unattended reinstall/reboot loops. Manual and periodic OTA writers share one runtime lock.

Persistent state is allowlisted rather than persisting the full root filesystem: NetworkManager Wi-Fi profiles, Tailscale state, SSH host identity, operator authorized keys, OTA state and bounded evidence.

## Security boundary

SSH remains reachable only through `tailscale0`. HTTP management is tailnet-first; a narrowly scoped RFC1918/IPv6-local HTTP path is allowed only so an operator physically present with the console pairing code can establish a session. LAN presence alone does not authorize management mutations.

OTA trust uses OpenSSH SSHSIG verification with a dedicated release public key. The corresponding private signing key is not stored in the repository or appliance.

Before any writable EFI access, boot/update paths verify that the relevant runtime slot, EFI and STATE devices share the same parent and that the parent transport is USB. The host-disk guard exempts only that validated CyberHIVE USB parent, regardless of the kernel removable bit, and treats writable mounts on every other physical disk as a violation.

The runtime updater does not perform partitioning or raw-device writes.

## Consequences

The node can be left unattended after one local Wi-Fi/Tailscale enrollment. Future normal runtime releases can be installed remotely even with only one physical USB. Crash recovery is conservative: an ambiguous or rolled-back candidate is quarantined and requires a newer signed sequence rather than being retried automatically.

The local physical-pairing fallback exposes HTTP to private/local address space, but management mutations still require the console pairing code. SSH does not gain a LAN fallback.

Bootloader-format changes still require a separate maintenance path and stronger authorization. Physical media failure remains outside A/B rollback coverage.

## Rejected alternatives

- Persisting the full live root filesystem: rejected because it expands state drift and rollback ambiguity.
- Updating the active slot in place: rejected because it removes the last known-good runtime.
- Treating `RM=0` as equivalent to an internal disk: rejected because USB SSDs commonly report `RM=0`; transport and validated parent identity are the correct boundary.
- Retrying a failed signed release indefinitely: rejected because it creates an unattended reboot loop.
- Allowing SSH on LAN for recovery: rejected because physical pairing needs only the HTTP pairing endpoint and LAN presence is not identity.

## Migration / rollback

This remains a proposed v0.3 development architecture. No existing physical v0.2 media is modified by this ADR. If the repair fails validation, revert the PR branch to the pre-repair head and keep the current v0.2 node online.
