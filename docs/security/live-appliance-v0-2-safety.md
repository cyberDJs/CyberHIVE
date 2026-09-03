# CyberHIVE Live Appliance v0.2 Security Boundary

## Threat model

Live Appliance v0.2 intentionally adds LAN-facing SSH and HTTP services. The primary threats are reusable default credentials, unintended root access, unauthenticated control actions, config-media abuse, accidental host-disk mutation and leakage of boot-session secrets into logs/evidence.

## SSH

Required:

- `PermitRootLogin no`
- public-key authentication enabled
- password authentication disabled when a valid config key is present
- no reusable password embedded in the image
- fallback password generated per boot
- fallback password shown only on the local physical console

## Config media

Only filesystems labeled `CYBERHIVE_CFG` are considered for automatic operator configuration.

Automatic mount requirements:

```text
ro,nodev,nosuid,noexec
```

The v0.2 bootstrap imports public `authorized_keys` only. It must not execute scripts from config media.

## Browser control

- LAN status endpoint may be readable before pairing
- control/state-changing endpoints require a boot-session pairing token
- pairing uses constant-time secret comparison
- pairing attempts are rate-limited per remote address
- session tokens are generated randomly per boot
- no temporary SSH password is returned by the HTTP API

TLS is not claimed for the first isolated-LAN prototype. This limitation must remain visible until a local certificate strategy exists.

## Host-disk boundary

Default boot must not intentionally mount fixed internal disks read-write.

`cyberhive-host-disk-guard` is an evidence/detection mechanism. It reports a failure if a mount backed by a non-removable physical disk is writable.

It must not automatically run:

- `mkfs`
- `wipefs`
- `parted`
- `fdisk`
- `dd`
- destructive filesystem repair
- automatic writable remount of host disks

## Remote help / DevBridge / MCP

Default state:

```text
remote help: disabled
DevBridge: disabled
MCP: disabled
```

A browser pairing event is not authority to enable any of these capabilities.

## Support bundle

The support bundle must exclude:

- `/run/cyberhive/**/ssh-password`
- pairing code/token files
- private SSH keys
- `/etc/shadow`
- environment files containing secrets

## Persistence

The live root remains ephemeral by default. The optional config medium is read-only in v0.2. Any future writable persistence overlay requires a separate design/security review.
