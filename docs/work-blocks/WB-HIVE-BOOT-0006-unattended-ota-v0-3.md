# WB-HIVE-BOOT-0006 - Unattended single-USB A/B OTA v0.3

Status: IMPLEMENTATION CANDIDATE - REPAIR VERIFICATION PENDING

## Goal

Turn the physically proven v0.2 live appliance into a development node that can be left unattended after one local bootstrap and subsequently updated remotely from a single USB device.

## Required behavior

- one-time local Wi-Fi selection and password entry on first physical boot
- Wi-Fi profile persists only on the removable CyberHIVE STATE partition
- Tailscale enrollment is one-time and its machine state persists on the USB
- OpenSSH is public-key only when persistent owner keys are present
- SSH management is tailnet-only
- HTTP management is tailnet-first; private/local HTTP exists only for physical-code pairing fallback
- web mutations trust authenticated tailnet peers or a valid physical-pairing session, never LAN presence alone
- stable EFI boot wrapper selects runtime slot A or B
- updates are written only to the inactive slot
- OTA manifest signature is verified before bundle download is trusted
- monotonically increasing signed release sequence blocks replay/downgrade and skips quarantined failed releases
- bundle byte count and SHA-256 are verified before slot promotion
- complete pending metadata is durable on STATE before GRUB is armed
- candidate boot must pass health before it becomes current
- commit is recoverable across STATE/EFI power-loss windows
- failed candidate userspace health causes reboot and rollback to the previous slot
- failed/rolled-back releases are quarantined to prevent unattended reboot loops
- manual and periodic OTA writers are serialized
- host internal disks remain outside the update/write surface, including when the CyberHIVE USB reports `RM=0`
- live boot disables host swap before userspace guard evaluation
- live-boot is constrained to the firmware-selected slot partition instead of globally scanning for the slot path, and visible duplicate selected-slot UUIDs are rejected before boot

## First bootstrap

The v0.3 raw disk image contains `CYBER_EFI`, `CYBERHIVE_A`, `CYBERHIVE_B` and `CYBERHIVE_STATE`. Initial runtime is slot A. The first local tty1 login invokes `cyberhive-firstboot`, which asks for Wi-Fi credentials with echo disabled and then performs an interactive Tailscale enrollment. No Wi-Fi password or Tailscale private machine state is committed to Git.

A bootstrap SSH public key is included so the owner can reach the node as soon as Tailscale is enrolled. Additional operator keys are added later to the persistent `state/ssh/authorized_keys` file without another USB rewrite.

## Single-USB update transaction

`current A -> GRUB selects slot by EFI parent + filesystem UUID -> lock -> verify common USB parent -> download signed bundle -> verify -> install B.new -> atomically promote B -> persist pending STATE metadata -> sync -> set GRUB pending_slot=B, previous_slot=A, tries=1 -> reboot -> health gate -> transactionally commit B or quarantine + reboot -> GRUB rollback A`.

The runtime updater never calls `dd`, `mkfs`, `wipefs`, `parted` or `sgdisk`. It mutates only the removable inactive slot partition, the matching STATE transaction journal and the matching removable EFI `grubenv`.

## Repair evidence target

Fresh review on head `dcf760420fcb4eaffdc530d19bbb70d57f39d043` found five P1 and three P2 defects covering missing-persistence rollback, EFI parent validation, pending/commit crash ordering, failed-release loops, OTA concurrency, USB `RM=0` handling and physical pairing reachability. The first approved image-only run also built the ISO but failed in the unattended A/B disk-image stage.

This repair must close those findings, pass the v0.3 validator and GitHub Actions, receive a fresh independent review, and complete a new exact-head image-only build before any USB write can be considered.

## Limitations

A/B protects software updates; it does not protect against physical USB failure. A hard kernel/firmware hang before userspace can require physical intervention if the platform watchdog cannot reset the machine. A second immutable rescue USB remains recommended but is not required for this bootstrap.

GPU compute enablement for the observed RTX 3070 is intentionally a follow-on remote change; v0.3 preserves inventory and remote reachability first.

## Governance

- base: exact PR #28 head `f1398376d54299c91212c62045f229781d60d45b`
- pre-repair v0.3 head: `dcf760420fcb4eaffdc530d19bbb70d57f39d043`
- merge: NOT AUTHORIZED
- image build: requires the existing exact-head image-only approval gate
- USB write: NOT AUTHORIZED by this work block
- internal host-disk writes: forbidden
- deployment/ADR acceptance: not implied
