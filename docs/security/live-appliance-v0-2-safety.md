# CyberHIVE Live Appliance v0.2 Security Boundary

## Threat model

Live Appliance v0.2 intentionally adds LAN-facing SSH and HTTP services. The primary threats are reusable default credentials, reused SSH host identity, unintended root access, unauthenticated control actions, network-service compromise, config-media abuse, accidental host-disk mutation and leakage of boot-session secrets into logs/evidence.

## SSH

Required:

- `PermitRootLogin no`
- public-key authentication enabled
- password authentication disabled when a valid config key is present
- no reusable password embedded in the image
- fallback password generated per boot
- fallback password shown only on the local physical console
- no reusable SSH host private keys embedded in the image
- SSH host keys generated into the ephemeral overlay each boot
- SSH host fingerprint shown to the operator for verification

Per-boot host keys mean a repeated hostname may legitimately present a different fingerprint after reboot. Persistent appliance host identity is a later enrollment/persistence decision and must not be faked by sharing one image-wide private key.

## Process / credential isolation

The LAN-facing browser control plane must not run as the interactive `cyberhive` SSH/login user.

Runtime identities:

```text
cyberhive      interactive console + SSH user
cyberhive-web  unprivileged browser-service user
cyberhive-control  bounded shared control/evidence group
```

The web service may read the pairing code and non-secret runtime state required for health/control. It must not have filesystem access to the ephemeral SSH password directory.

The per-boot SSH password stays under `/run/cyberhive/private` with access for root and the interactive `cyberhive` identity only. Pairing/session state belongs to the bounded control surface instead of the SSH-private directory.

## Config media

Only filesystems labeled `CYBERHIVE_CFG` are considered for automatic operator configuration.

Automatic mount requirements:

```text
ro,nodev,nosuid,noexec
```

The v0.2 bootstrap imports public `authorized_keys` only. It must not execute scripts from config media.

If the matching filesystem is already mounted writable, automatic key import is rejected rather than silently trusting the writable mount.

## Browser control

- browser service runs as `cyberhive-web`, not as the SSH/login user
- LAN status endpoint may be readable before pairing
- control/state-changing endpoints require a boot-session pairing token
- pairing uses constant-time secret comparison
- pairing attempts are rate-limited per remote address
- session tokens are generated randomly per service/boot session
- no temporary SSH password is returned by the HTTP API
- no remote-help enable endpoint exists in v0.2
- systemd constrains the service with `NoNewPrivileges`, home isolation and only `CAP_NET_BIND_SERVICE`

TLS is not claimed for the first isolated-LAN prototype. This limitation must remain visible until a local certificate strategy exists.

## Host-disk boundary

Default boot must not intentionally mount fixed internal disks read-write.

`cyberhive-host-disk-guard` is an evidence/detection mechanism. It reports a failure if a mount backed by a non-removable physical disk is writable.

It must not automatically run destructive disk commands or writable-remount logic.

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

- temporary SSH password files
- pairing code/token files
- private SSH keys
- `/etc/shadow`
- environment files containing secrets

## Persistence

The live root remains ephemeral by default. The optional config medium is read-only in v0.2. Any future writable persistence overlay requires a separate design/security review.
