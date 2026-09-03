# WB-HIVE-BOOT-0005 Implementation Checkpoint

## Exact state before PR creation

```text
branch: wb-hive-boot-0005-live-appliance-v0-2
head: 9c6c852aae25912f31ffdcab7c8f67b8fcd63cba
stacked base: wb-hive-boot-0004-real-image-build-gate
stacked base expected head: 63c14dba7fd28b8a0d53c23bbda766b06d950260
```

## Implemented

- Live Appliance v0.2 roadmap and project-context update
- physical boot/media evidence receipt
- CyberDJS/CyberHIVE reviewable boot SVG source
- deterministic boot-raster export dependency
- `openssh-server` with key-first / ephemeral-password bootstrap
- per-boot SSH host keys and visible fingerprint
- `CYBERHIVE_CFG` read-only key import
- dynamic local welcome and QR onboarding
- mDNS advertisement for `cyberhive.local`
- local browser control plane with boot-session pairing
- role-intent selection without implicit MCP/DevBridge enablement
- host-disk guard
- support bundle
- v0.2 CI validation contract

## Verification state

Local clean-clone verification was attempted but the verifier sandbox could not resolve `github.com`; this is an environment limitation, not a test result.

GitHub Actions on the draft PR is the next independent verifier.

## Authority state

```text
merge: NOT AUTHORIZED
v0.2 real image build: NOT AUTHORIZED by this checkpoint
USB rewrite: NOT AUTHORIZED
v0.2 physical boot: NOT VERIFIED
DevBridge/MCP: NOT ENABLED
remote help: NOT ENABLED
ADR-0009 accepted: NO
```
