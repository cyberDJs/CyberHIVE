# Threat Model — CyberHIVE Live USB

## Scope

This document covers the first CyberHIVE Live USB runtime artifact and its boot, local runtime, DevBridge, storage and network exposure boundaries.

## Assets

- host hardware safety,
- host disks and user data,
- CyberHIVE node identity,
- enrollment material,
- cache artifacts,
- logs/evidence,
- runtime configuration,
- DevBridge/MCP access,
- local network trust boundary.

## Trust assumptions

CyberHIVE assumes:

- the LAN is not trusted,
- peers are not trusted until enrolled,
- cache content may be corrupt or malicious,
- local disks may contain sensitive data,
- borrowed hardware may not be clean,
- mobile and weak peers may disappear,
- network state may change during execution.

## Threats

### Host disk mutation

Risk: live USB accidentally or maliciously writes to internal disks.

Controls:

- no automount read-write by default,
- explicit operator action for host disk mutation,
- disk state visible in dashboard/diagnostics,
- smoke test for mount policy where practical.

### Secret exposure

Risk: image, logs, evidence or DevBridge output leak secrets.

Controls:

- no secrets baked into image,
- secret scanning in repository/CI,
- redaction policy for logs/evidence,
- no credential dump commands in first DevBridge.

### Unauthorized remote control

Risk: SSH/MCP/DevBridge opens automatically.

Controls:

- disabled by default,
- explicit local enablement,
- one-time enrollment or token flow for first access,
- clear runtime indicator when enabled,
- audit log for remote actions.

### Malicious peer

Risk: a peer advertises false capabilities or attempts to receive/execute unauthorized work.

Controls:

- cryptographic identity before trust,
- signed capabilities where applicable,
- policy-based task assignment,
- capability freshness checks,
- result verification and receipts.

### Cache poisoning

Risk: corrupted or malicious cache object is reused.

Controls:

- content-addressed storage,
- digest verification before use,
- quarantine on mismatch,
- never treat cache hit as proof without verification.

### Weak-network partial state

Risk: interrupted transfers or task dispatch produce ambiguous state.

Controls:

- resumable transfers where practical,
- partial state preserved,
- no false success from ACK alone,
- explicit reconciliation.

### DevBridge misuse

Risk: development bridge becomes a general remote shell or exfiltration path.

Controls:

- first slice allows only bounded actions,
- no destructive commands,
- audit all commands,
- local enablement required,
- easy disable/reset.

## Security requirements for first implementation

- DevBridge disabled by default,
- no inbound remote service unless role explicitly enables it,
- no host disk write by default,
- logs/evidence avoid secrets by default,
- build artifact manifest produced,
- image hash recorded,
- known unsafe behaviors block promotion.

## Out of scope for first image

- production-grade secure boot chain,
- public federation,
- tenant isolation,
- marketplace abuse protection,
- certificate rotation automation,
- full mobile platform security model.
