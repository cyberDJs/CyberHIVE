# CyberHIVE Live USB Safety Boundary

## Default posture

The live USB must boot safely on owned or borrowed hardware.

Default behavior is conservative:

- observe before acting,
- do not mutate host disks,
- do not trust peers by proximity,
- do not expose remote control without explicit local action,
- preserve evidence without leaking secrets.

## Hard rules

1. No secrets are baked into the image.
2. No credentials, tokens, private keys or enrollment material are committed to the repository.
3. SSH, MCP and DevBridge are disabled by default.
4. Enabling remote development requires explicit local confirmation after boot.
5. Internal disks are read-only or untouched by default.
6. Persistent USB overlay is explicit and inspectable.
7. Destructive host operations are outside the first implementation.
8. Cache content is never trusted without digest verification.
9. Peer identity is cryptographic, not LAN-based.
10. Logs and evidence exports must avoid secret disclosure by default.

## DevBridge / MCP boundary

First DevBridge slice may support:

- health checks,
- hardware inventory,
- log reading,
- evidence export,
- allowed test commands,
- repository checkout into a workspace,
- CyberHIVE-specific development commands.

First DevBridge slice must not support:

- unrestricted shell,
- disk erase/format/partition mutation,
- credential extraction,
- automatic persistence enablement,
- unauthenticated inbound access,
- automatic external tunneling.

## Host disk boundary

The live environment must distinguish:

- live system storage,
- RAM state,
- USB persistent overlay,
- internal host disks,
- removable non-boot disks.

Host disks must not be mounted read-write automatically.

## Evidence boundary

Evidence should include enough facts to debug and verify behavior without dumping private user data.

Safe by default:

- CPU/RAM/GPU summary,
- OS and kernel summary,
- network interface names and link status,
- CyberHIVE service status,
- package/build manifest,
- non-secret error logs.

Sensitive by default:

- Wi-Fi passwords,
- tokens and SSH keys,
- private IP topology when classified,
- mounted user files,
- browser/session data,
- shell history,
- private model prompts or datasets.
