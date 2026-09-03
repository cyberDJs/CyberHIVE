# WB-HIVE-BOOT-0005 — physical runtime evidence — 2026-09-03

## Scope

Physical boot and local runtime observation of the v0.2 image built from PR #28 head `a8e38ae1a6b76bbdd51d017b9e06feb0277bb9a6`.

This evidence does not authorize merge, deployment, host-disk writes, MCP/DevBridge enablement, remote-help enablement, or ADR acceptance.

## Evidence identity

- operator-supplied console photograph: `Screenshot 2026-09-03 at 23.12.33.png`
- bytes: `4712178`
- SHA-256: `979cd8cead5c8ddcaaa75c24300d1d1edc792a4d145562047154a4bdd7994aac`

## Observed PASS

- physical UEFI boot reached the CyberHIVE live appliance console
- hostname: `cyberhive-live`
- version: `0.2.0-dev`
- DHCP IPv4: `192.168.1.122`
- mDNS service reported `active`
- host-disk guard reported `pass`
- root source reported `overlay`
- root filesystem type reported `overlay`
- persistence reported `ephemeral`
- DevBridge, MCP and Remote Help reported `disabled`
- boot-session ID, pairing code and ephemeral SSH password were generated

## Observed FAIL

- browser connection to both `cyberhive.local` and the displayed IPv4 was refused
- `cyberhive-live-health` reported web service `inactive`
- SSH connection was refused
- `cyberhive-live-health` reported SSH service `inactive`
- SSH host fingerprint remained `unknown` / `initializing`
- expected branded boot splash was not visible during physical boot
- health JSON incorrectly reported top-level `status: ok` despite required local-control services being inactive

## Failure boundary

The generated session, pairing code, auth mode and ephemeral password prove that `cyberhive-onboarding-init` progressed through common bootstrap and password setup. The missing SSH fingerprint shows it did not complete the later SSH validation section.

The v0.2 implementation called `sshd -t` before `ssh.service` started. Debian OpenSSH normally creates `/run/sshd` through the service RuntimeDirectory, so early standalone validation can fail while that directory is absent. Because both SSH and the browser control plane depended on the onboarding unit, a late SSH bootstrap failure propagated to both services.

The boot branding implementation also targeted `config/bootloaders/grub-efi`; live-build 1:20230502 uses `config/bootloaders/grub-pc` as the shared configuration source for both grub-pc and grub-efi, so the UEFI path did not receive the custom splash.

## Repair

The PR #28 branch is repaired after this evidence with:

1. explicit creation of ephemeral `/run/sshd` before `sshd -t`;
2. persisted SSH bootstrap status and fingerprint evidence;
3. browser service ordered after onboarding but not hard-required by the SSH bootstrap failure domain;
4. degraded top-level health when onboarding/SSH/web/mDNS/host-guard requirements are not healthy;
5. GRUB branding moved to `config/bootloaders/grub-pc` with post-build hash verification of `binary/boot/grub/splash.png`;
6. regression guards for these runtime and EFI-branding contracts.

## Current terminal state

`PHYSICAL_BOOT = PASS`

`V0.2_RUNTIME_ACCEPTANCE = FAILED / REPAIR_PENDING_REBUILD`

A new exact-head image build, USB rewrite and physical re-test are required before v0.2 runtime acceptance can become PASS.
