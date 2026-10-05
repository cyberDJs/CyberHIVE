# CyberHIVE Live Appliance v0.3 runbook

## First physical boot

1. Boot the v0.3 CyberHIVE USB in UEFI mode.
2. Wait for tty1 auto-login and the first-boot wizard.
3. Select/enter the Wi-Fi SSID locally and enter the Wi-Fi password at the hidden prompt.
4. Open the printed Tailscale enrollment URL on a trusted device and authorize `cyberhive-dev-01`.
5. Confirm the welcome screen reports a Tailscale address and key-based SSH mode.

Do not send Wi-Fi credentials, Tailscale auth material or private SSH keys through chat, Slack or GitHub.

## Physical validation invariants

On Acer-class UEFI firmware the standalone loader may expose `cmdpath=(hd0,gpt1)/EFI/BOOT`. The embedded GRUB logic must derive `boot_disk=hd0`, construct slot A as `(hd0,gpt2)/slots/A` (slot B as GPT3), and pass `cyberhive.slot=A|B` on the kernel command line. A value such as `(,gpt2)` is a bootloader parent-detection failure, not a missing slot payload.

`/run/cyberhive/state/persistence-state` is non-secret operational health metadata. It must be readable by the unprivileged `cyberhive-live-health` / welcome path while persistent STATE contents, Tailscale state, SSH keys and OTA state remain protected. The expected successful form is `mounted:<state-device>:<usb-parent>:<slot>`.

## Normal unattended boot

The appliance mounts `CYBERHIVE_STATE`, restores saved Wi-Fi profiles, bind-mounts persistent Tailscale state, restores persistent SSH host keys and owner authorized keys, starts Tailscale, SSH and the web service, and runs the boot health gate.

SSH is reachable only through `tailscale0`. HTTP is tailnet-first. A private/local HTTP path exists for physical-console pairing; possession of a LAN address is not authorization and management mutations still require the pairing code/session.

## Remote update

A signed DEV channel manifest can be applied manually with:

```bash
sudo cyberhive-update --manifest https://example.invalid/channel.json --reboot
```

The signature must be available at the same URL with `.sig` appended. The updater accepts only schema `cyberhive.ota.manifest.v1`, channel `dev`, the configured release signer, a sequence newer than the committed/quarantined sequence floor, an exact bundle byte count and SHA-256.

Manual and periodic updates share one runtime lock. If another OTA operation is active, a second writer fails closed and the periodic timer can retry later.

The periodic timer checks the configured DEV channel URL every 30 minutes. A missing channel document is a no-op.

## Rollback and crash recovery

The updater never overwrites the running slot. It persists the complete pending transaction to STATE before arming GRUB. A candidate gets one pending boot. `cyberhive-boot-commit` waits up to 120 seconds for SSH, web, Tailscale and the CyberHIVE health/host guard to become healthy.

PASS advances persistent anti-downgrade state before clearing EFI pending state. A recovery transaction allows the next boot to finish or reverse an interrupted commit safely.

FAIL stores the failed release ID/sequence and reboots. GRUB returns to the previous slot, and the periodic updater refuses the quarantined release so the machine does not enter a reinstall/reboot loop.

If the candidate cannot mount `CYBERHIVE_STATE`, it reboots without writing an unverified EFI target; GRUB then rolls back. The previous slot reconciles the stale pending metadata and quarantines the candidate.

## Image-only build diagnostics

The governed image build records disk usage before and after deleting disposable live-build work trees and uploads a lightweight diagnostic artifact containing logs, manifests, hashes and the traced unattended builder console. This evidence is diagnostic only; it does not prove physical boot or USB acceptance.

## Recovery boundary

If firmware, the kernel, or hardware hangs before userspace and no working hardware watchdog resets the machine, physical intervention can still be required. A second immutable rescue USB remains recommended when available, but v0.3 is designed so normal runtime updates do not require one.

## v0.3.1 offline-safe health contract

WB-HIVE-BOOT-0009 splits runtime health into three deterministic classes:

- LOCAL_SAFE: local boot/storage/security/control-plane contract,
- CONNECTED: non-Tailscale local network availability,
- REMOTE_READY: Tailscale remote-management readiness.

OTA candidate acceptance is based on LOCAL_SAFE. Internet, DNS, Tailscale backend state and Tailscale IP are not candidate acceptance requirements.

The top-level health schema remains cyberhive.live.health.v1 for compatibility. The new health object carries local_safe, connected, remote_ready and deterministic reason lists. Top-level status is ok exactly when LOCAL_SAFE passes.

This work block does not add Guardian repair actions. CONNECTED or REMOTE_READY failure is reported only; automated reconnection/restart policy is a later work block.

## v0.3.1 bounded Guardian L0/L1 repair

WB-HIVE-BOOT-0010 adds a one-shot Guardian evaluated once per minute by cyberhive-guardian.timer.

The Guardian performs at most one allowlisted repair per run and persists retry/circuit state under state/guardian on the validated CyberHIVE STATE partition.

Repair budget per action:

- 3 attempts within 10 minutes,
- at least 60 seconds between attempts,
- 15 minute circuit-open interval after exhaustion.

Automatic actions are limited to restarting web/SSH/mDNS/tailscaled and asking NetworkManager to reconnect existing profiles.

Every repair rechecks the host-disk guard and requires the management firewall service to be active. SSH restart additionally requires sshd -t to pass.

The Guardian does not reboot, modify GRUB/EFI/A-B slots, create network credentials, run tailscale up or weaken management authentication.

Operational inspection:

~~~
systemctl status cyberhive-guardian.timer
systemctl status cyberhive-guardian.service
cat /run/cyberhive/evidence/guardian.json
sudo cat /var/lib/cyberhive-persist/state/guardian/state.json
~~~

Malformed Guardian state, persistence failure, onboarding failure, host-disk-guard failure or firewall failure is fail-closed and requires operator intervention or a later recovery work block.
