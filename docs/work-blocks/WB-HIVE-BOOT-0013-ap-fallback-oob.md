# WB-HIVE-BOOT-0013 - AP fallback + true headless OOB onboarding

## Status

IN PROGRESS / NOT MERGEABLE.

Branch: `wb-hive-boot-0013-ap-fallback-oob`
Verified parent stack: `04a2504894caa7a608c41c56b2ebe3bc88bfcd1e` (WB-HIVE-BOOT-0011 merged into the boot stack).
WB-HIVE-BOOT-0012: no repository branch, commit, PR or work-block document found as of 2026-10-07.

## Goal

Provide deterministic local-first network recovery and onboarding without requiring a monitor, keyboard, serial console, Internet service or public endpoint.

## Required behavior

- Ethernet first.
- Saved Wi-Fi second.
- Bounded no-uplink detection.
- AP fallback only after the bounded window.
- Per-installation provisioning credential.
- Provisioning service bound only to the fallback network.
- Wi-Fi scan and credential submission.
- Transactional candidate apply.
- L3 verification before AP shutdown/persistence.
- Failed candidate restores AP.
- Reboot restores successful saved Wi-Fi.
- Later loss of every usable uplink restores AP.
- No expansion of the normal management plane.

## Security invariants

- LAN presence is not identity.
- The fallback AP must not be open in the production-accepted design.
- Provisioning credentials must never be logged.
- The normal CyberHIVE web service must not gain broad NetworkManager/root authority.
- OOB onboarding must not expose role, SSH, support, OTA, Guardian or Tailscale management.
- Existing management-firewall and SSH behavior from earlier boot WBs is preserved.
- Credential delivery itself is a required real-device acceptance item.

## Current implementation state

The dedicated systemd service unit is staged.

The runtime controller write is currently blocked by the execution platform's safety gate because it combines AP creation with upstream Wi-Fi credential handling. No bypass is authorized or attempted.

This means the work block is not complete and must not be reported as PASS.

## Promotion boundary

NO production deploy.
NO DNS.
NO public exposure.
NO USB write.
NO merge until exact-head CI and real-device boot/onboarding verification pass.
