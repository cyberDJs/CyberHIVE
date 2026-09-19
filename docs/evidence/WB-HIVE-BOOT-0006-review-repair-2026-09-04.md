# WB-HIVE-BOOT-0006 review repair evidence - 2026-09-04

Status: REPAIR CANDIDATE / VERIFICATION PENDING

## Source identity

- repository: `cyberDJs/CyberHIVE`
- pull request: `#29`
- pre-repair exact head: `dcf760420fcb4eaffdc530d19bbb70d57f39d043`
- failed image-only workflow run: `33916432898`
- failed job: `101164563192`
- uploaded evidence artifact: `9953555870`
- artifact digest: `sha256:ef66d2629665ac7988b869370c62864179a4bc5d375333f7e09da860164192d0`

## Observed failures

The exact-head image gate and v0.3 static validator passed, and the Debian live ISO was created. The subsequent unattended A/B disk-image stage exited with status 1. The original workflow uploaded a large combined artifact but did not provide a separately inspectable lightweight console trace for that stage.

Fresh Codex review on the same head reported eight unresolved findings:

1. P1 - candidate with unavailable STATE could remain running instead of rebooting into GRUB rollback.
2. P1 - boot commit could mount a label-selected EFI partition writable before proving it belongs to the CyberHIVE USB.
3. P1 - updater armed GRUB before pending anti-downgrade metadata was durable.
4. P1 - candidate commit cleared GRUB pending state before durable anti-downgrade state, creating a power-loss inconsistency window.
5. P1 - a failed release was not quarantined and could be reinstalled forever by the timer.
6. P2 - manual and periodic OTA writers were not serialized.
7. P2 - host-disk guard treated `RM=0` as internal even for validated USB media.
8. P2 - firewall policy made the claimed physical HTTP pairing fallback unreachable.

## Repair change units

### OTA transaction and rollback

- one runtime OTA lock serializes updater and boot-commit state mutation;
- pending release metadata is atomically written and synced to STATE before GRUB is armed;
- boot commit validates current-slot/EFI/STATE parent identity and `TRAN=usb` before writable EFI access;
- missing STATE on a pending candidate requests a reboot without writable EFI access so GRUB can roll back;
- commit uses a recovery transaction with old/new release state; anti-downgrade STATE advances before EFI pending state is cleared;
- stale or failed pending releases are quarantined by release ID and sequence so the timer requires a newer sequence.

### Host-disk guard

- only the validated STATE-backed USB parent is exempt from host-disk violations;
- kernel `RM` is no longer used as the deciding identity signal;
- writable mounts on every other physical disk remain violations.

### Management fallback

- SSH remains tailnet-only;
- HTTP is dropped on non-tailnet interfaces except loopback/private/link-local source ranges needed for physical-code pairing;
- DROP is installed before ACCEPT exceptions because rules are inserted at INPUT position 1.

### Image build observability

- disposable live-build `.work` trees are removed before constructing the 6 GiB A/B disk image to reduce runner disk pressure;
- pre/post cleanup disk usage and `sh -x` unattended-builder output are captured;
- lightweight diagnostics are uploaded separately from large image artifacts.

## Verification required before USB consideration

- shell syntax and repair regression assertions pass locally;
- exact-head GitHub v0.3 validation passes;
- all relevant GitHub Actions pass;
- fresh independent Codex review has no unresolved valid P1/P2 finding;
- a new explicitly approved exact-head image-only build produces `.img.gz`, `.slot.tar`, hashes, manifest and diagnostic evidence successfully.

This evidence does not authorize merge, USB/media write, physical boot, persistence acceptance, OTA/rollback physical acceptance, deployment or ADR acceptance.
