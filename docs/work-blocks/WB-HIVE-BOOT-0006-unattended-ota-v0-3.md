# WB-HIVE-BOOT-0006 — Unattended single-USB A/B OTA v0.3

Status: IMPLEMENTATION CANDIDATE

## Goal

Turn the physically proven v0.2 live appliance into a development node that can be left unattended after one local bootstrap and subsequently updated remotely from a single USB device.

## Required behavior

- one-time local Wi-Fi selection and password entry on first physical boot
- Wi-Fi profile persists only on the removable CyberHIVE STATE partition
- Tailscale enrollment is one-time and its machine state persists on the USB
- OpenSSH is public-key only when persistent owner keys are present
- SSH and web management are blocked on non-`tailscale0` interfaces
- web mutations trust authenticated tailnet peers; physical pairing remains only a local fallback
- stable EFI boot wrapper selects runtime slot A or B
- updates are written only to the inactive slot
- OTA manifest signature is verified before bundle download is trusted
- monotonically increasing signed release sequence blocks replay/downgrade of older DEV releases
- bundle byte count and SHA-256 are verified before slot promotion
- candidate boot must pass health before it becomes current
- failed candidate userspace health causes reboot and rollback to the previous slot
- host internal disks remain outside the update/write surface

## First bootstrap

The v0.3 raw disk image contains `CYBERHIVE_EFI`, `CYBERHIVE_A`, `CYBERHIVE_B` and `CYBERHIVE_STATE`. Initial runtime is slot A. The first local tty1 login invokes `cyberhive-firstboot`, which asks for Wi-Fi credentials with echo disabled and then performs an interactive Tailscale enrollment. No Wi-Fi password or Tailscale private machine state is committed to Git.

A bootstrap SSH public key is included so the owner can reach the node as soon as Tailscale is enrolled. Additional operator keys, including Eimy, are added later to the persistent `state/ssh/authorized_keys` file without another USB rewrite.

## Single-USB update transaction

`current A -> download signed bundle -> verify -> install B.new -> atomically promote B -> set pending_slot=B, previous_slot=A, tries=1 -> reboot -> health gate -> commit B or reboot -> GRUB rollback A`.

The runtime updater never calls `dd`, `mkfs`, `wipefs`, `parted` or `sgdisk`. It mutates only the removable inactive removable slot partition and the GRUB environment block on the matching removable EFI partition.

## Limitations

A/B protects software updates; it does not protect against physical USB failure. A hard kernel/firmware hang before userspace can require physical intervention if the platform watchdog cannot reset the machine. A second immutable rescue USB remains recommended but is not required for this bootstrap.

GPU compute enablement for the observed RTX 3070 is intentionally a follow-on remote change; v0.3 preserves inventory and remote reachability first.

## Governance

- base: exact PR #28 head `f1398376d54299c91212c62045f229781d60d45b`
- merge: NOT AUTHORIZED
- image build: requires the existing exact-head image-only approval gate
- USB write: NOT AUTHORIZED by this work block
- internal host-disk writes: forbidden
- deployment/ADR acceptance: not implied
