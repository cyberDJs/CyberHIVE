# Live Appliance v0.3 safety boundary

## Allowed persistent writes

Only the removable parent disk that contains both `CYBERHIVE_EFI`, `CYBERHIVE_A`, `CYBERHIVE_B` and `CYBERHIVE_STATE` is an appliance persistence/update target. Persistent writes are limited to:

- `state/network/` — root-only NetworkManager profiles
- `state/tailscale/` — Tailscale machine state
- `state/ssh/` — SSH host keys and authorized public keys
- `state/ota/` — release and rollback state
- `state/evidence/` — bounded non-secret health evidence
- `CYBERHIVE_A` and `CYBERHIVE_B` partitions — one active read-only live slot and one inactive OTA target
- the EFI `cyberhive/grubenv` boot-state file

## Forbidden

- raw runtime writes to `/dev/sd*`, NVMe, SATA or other host disks
- persisting Wi-Fi passwords or Tailscale private state in Git
- storing the OTA release private signing key on CyberHIVE
- exposing SSH or the web control plane directly to the local LAN or internet by default
- accepting a signed DEV release whose sequence is not newer than the committed sequence
- automatic bootloader replacement through the ordinary DEV channel
- treating successful download/build/write as runtime acceptance

## OTA verification order

1. fetch manifest and signature over HTTPS
2. verify SSHSIG namespace and dedicated signer identity
3. validate manifest schema/channel and monotonic release sequence
4. download bundle
5. verify exact bytes and SHA-256
6. validate exact archive path allowlist
7. install inactive slot
8. update GRUB pending state
9. reboot
10. commit only after runtime health PASS

## Secret handling

The repository contains public SSH keys only. First-boot Wi-Fi entry uses a no-echo local tty prompt. Support/evidence tooling must not read NetworkManager secrets, Tailscale state, SSH private host keys, pairing codes, passwords or the release signing private key.
