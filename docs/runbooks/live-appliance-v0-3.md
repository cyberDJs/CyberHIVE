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

SSH and HTTP management are intended to be reachable only through `tailscale0`. Tailnet peers do not need the per-boot physical pairing code; Tailscale identity/ACL is the remote web trust boundary.

## Remote update

A signed DEV channel manifest can be applied manually with:

```bash
sudo cyberhive-update --manifest https://example.invalid/channel.json --reboot
```

The signature must be available at the same URL with `.sig` appended. The updater accepts only schema `cyberhive.ota.manifest.v1`, channel `dev`, the configured release signer, a sequence newer than the last committed release, an exact bundle byte count and SHA-256.

The periodic timer checks the configured DEV channel URL every 30 minutes. A missing channel document is a no-op.

## Rollback

The updater never overwrites the running slot. A candidate gets one pending boot. `cyberhive-boot-commit` waits up to 120 seconds for SSH, web, Tailscale and the CyberHIVE health/host guard to become healthy. PASS commits the candidate. FAIL forces the next reboot back to the previous slot.

## Recovery boundary

If firmware, the kernel, or hardware hangs before userspace and no working hardware watchdog resets the machine, physical intervention can still be required. Keep a second immutable rescue USB when available.
