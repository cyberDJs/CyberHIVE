# WB-HIVE-BOOT-0005 Source Map

## Work block

`WB-HIVE-BOOT-0005 — CyberHIVE Live Appliance v0.2`

## Parent exact state

- repository: `cyberDJs/CyberHIVE`
- parent branch: `wb-hive-boot-0004-real-image-build-gate`
- parent exact head: `63c14dba7fd28b8a0d53c23bbda766b06d950260`
- parent PR: #27

## Physical evidence inputs

- approved image-build run: GitHub Actions run `33785844714`
- ISO SHA-256: `a93778f299031a0eab340f75e95ed600c5cef315c0678929b36b093ccb023b49`
- ISO bytes: `861929472`
- media write: `dd` exit 0
- media readback: `cmp -n 861929472` exit 0
- physical boot: photographed 2026-09-03
- physical network observation: `192.168.1.122/24`
- physical SSH observation: `ssh.service` and `sshd.service` not found in v0.1

## User-approved product direction

- boot CyberDJS graphics
- browser-first LAN administration
- SSH mode 3C: config public key or per-boot temporary password
- first-boot wizard
- QR onboarding
- immutable/resettable model
- network auto-discovery
- support/evidence bundle
- remote-help/pairing foundation
- later desktop/prompt surface sharing the same web control plane

## External implementation reference

Debian Live documentation defines `config/bootloaders` as the bootloader customization path and describes a 640x480 `splash.png` background for a personalized boot menu.

## Authority state

- branch implementation: authorized by user
- merge: NOT AUTHORIZED
- new v0.2 image build: requires the existing image-only build gate authority
- USB rewrite: NOT AUTHORIZED by this work block
- v0.2 physical boot claim: NOT YET VERIFIED
- ADR-0009: PROPOSED / NOT ACCEPTED
