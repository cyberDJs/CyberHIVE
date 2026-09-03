# Roadmap

## M0 — Bootstrap

- [x] dedicated GitHub repository
- [x] Drive project structure
- [x] project context and agent rules
- [x] first three reusable skills prepared
- [ ] ADR-0001 approve architecture baseline
- [x] choose Debian 12/bookworm as the first Live USB candidate base
- [ ] choose inference runtime experiment matrix

## M1 — Single-node appliance

### M1.0 — Live USB proof

- [x] repeatable Debian Live configuration skeleton
- [x] dry-run and real-build plan gates
- [x] explicitly approved real image-only build
- [x] preserved image, manifest and SHA-256 evidence
- [x] verified USB media write with byte-for-byte readback
- [x] physical x86_64 boot smoke on 2026-09-03
- [ ] close runtime host-disk-safety evidence with machine-readable guard output

### M1.1 — CyberHIVE Live Appliance v0.2

Work block: `WB-HIVE-BOOT-0005`.

- [ ] CyberDJS/CyberHIVE boot branding from reviewable repository source
- [ ] dynamic local welcome screen with node/IP/URL/SSH state
- [ ] browser-first control surface at `http://cyberhive.local`
- [ ] fallback browser URL using detected IPv4 address
- [ ] QR onboarding on the local console
- [ ] SSH 3C bootstrap: `authorized_keys` from `CYBERHIVE_CFG` when present, otherwise ephemeral boot password
- [ ] disable SSH root login and disable password auth automatically when key mode is active
- [ ] first-boot role wizard in the browser
- [ ] local pairing code before browser control actions
- [ ] immutable/read-only live root with explicit persistence boundary
- [ ] host-disk guard that detects and reports unexpected writable internal-disk mounts
- [ ] health, hardware inventory and support/evidence bundle from browser and CLI
- [ ] remote-help control surface remains explicit and disabled by default
- [ ] version/build/session identity visible in console and browser
- [ ] Safe Mode / Diagnostics boot entries

### M1.2 — Runtime control plane

- [ ] one model runtime adapter
- [ ] stable local API
- [ ] health and logs API
- [ ] update + rollback prototype
- [ ] governed DevBridge/MCP enable flow

### M1.3 — Local desktop and prompt surface

Desktop is deliberately downstream of the browser control plane so the same UI/API is reused locally and remotely.

- [ ] lightweight optional desktop profile
- [ ] auto-open CyberHIVE local web UI in kiosk/app mode
- [ ] prompt composer
- [ ] plan / approval / execution / evidence view
- [ ] local model/runtime selector

## M2 — Multi-node hive

- [ ] node identity/enrollment
- [ ] worker heartbeat/capability reporting
- [ ] scheduling
- [ ] secure remote transport
- [ ] explicit remote-help session grants and audit

## M3 — Productization

- [ ] installer/appliance images
- [ ] release signing
- [ ] support matrix
- [ ] documented backup/recovery
- [ ] plugin/skill registry hardening
- [ ] supported persistence/config-media provisioning workflow
