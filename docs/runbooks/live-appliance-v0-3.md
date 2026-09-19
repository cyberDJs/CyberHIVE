# CyberHIVE Live Appliance v0.3 runbook

## First physical boot

1. Boot the v0.3 CyberHIVE USB in UEFI mode.
2. Wait for tty1 auto-login and the first-boot wizard.
3. Select/enter the Wi-Fi SSID locally and enter the Wi-Fi password at the hidden prompt.
4. Open the printed Tailscale enrollment URL on a trusted device and authorize `cyberhive-dev-01`.
5. Confirm the welcome screen reports a Tailscale address and key-based SSH mode.

Do not send Wi-Fi credentials, Tailscale auth material or private SSH keys through chat, Slack or GitHub.

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
