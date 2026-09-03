# WB-HIVE-BOOT-0005 — physical runtime evidence — 2026-09-03

## Scope

Physical boot and local runtime observation of the v0.2 image built from PR #28 head `a8e38ae1a6b76bbdd51d017b9e06feb0277bb9a6`.

This evidence does not authorize merge, deployment, host-disk writes, MCP/DevBridge enablement, remote-help enablement, or ADR acceptance.

## Evidence identity — initial boot

- operator-supplied console photograph: `Screenshot 2026-09-03 at 23.12.33.png`
- bytes: `4712178`
- SHA-256: `979cd8cead5c8ddcaaa75c24300d1d1edc792a4d145562047154a4bdd7994aac`

## Observed PASS — initial boot

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

## Observed FAIL — initial boot

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

## Repair implemented on PR #28

1. explicit creation of ephemeral `/run/sshd` before `sshd -t`;
2. persisted SSH bootstrap status and fingerprint evidence;
3. browser service ordered after onboarding but not hard-required by the SSH bootstrap failure domain;
4. degraded top-level health when onboarding/SSH/web/mDNS/host-guard requirements are not healthy;
5. GRUB branding moved to `config/bootloaders/grub-pc` with post-build hash verification of `binary/boot/grub/splash.png`;
6. regression guards for these runtime and EFI-branding contracts.

## Ephemeral repair proof on the already-booted image

Before rebuilding the image, the SSH runtime prerequisite was repaired in the live overlay by creating `/run/sshd`, then restarting onboarding, SSH and the browser service. This modifies only the ephemeral live runtime and does not change the USB image.

Second operator-supplied console photograph:

- file: `Screenshot 2026-09-03 at 23.54.51.png`
- bytes: `4923447`
- SHA-256: `863939d7c6d8dff9fb87f7a488c86ec54b621c084383ba64bcd76b1cbcdb8596`

The console health output after the ephemeral repair showed:

- top-level health `status: ok`
- SSH service `active`
- SSH auth mode `ephemeral-password`
- SSH host fingerprint populated rather than `unknown`
- browser service `active`
- mDNS service `active`
- host-disk guard `pass`
- root still `overlay` / `ephemeral`
- DevBridge, MCP and Remote Help still `disabled`

No password or pairing code is recorded in this evidence document.

## Independent LAN verification of the ephemeral repair

A separate authorized Mac on the same LAN independently verified the repaired runtime:

- `cyberhive.local` resolved to IPv4 `192.168.1.122`
- `http://192.168.1.122/` returned HTTP `200`
- `http://cyberhive.local/` returned HTTP `200`
- TCP port 22 accepted a connection
- network `ssh-keyscan` returned ED25519 fingerprint `SHA256:BbdXknUB771teLe2TUmhLVkGxn2/UMSUKtLC9lB4c9o`
- that fingerprint exactly matched the fingerprint shown by the repaired local CyberHIVE health output

This independently confirms that the `/run/sshd` bootstrap repair restores reachable SSH and browser services and that mDNS discovery works on the tested LAN.

## Interactive SSH login verification

Third operator-supplied screenshot:

- file: `Screenshot 2026-09-04 at 0.01.32.png`
- bytes: `1371944`
- SHA-256: `ae487a0cf21352fdf7bfb55e050c854a5850eaff945ca1087b10f28452099c69`

The screenshot shows an interactive SSH connection from another LAN machine to `cyberhive@192.168.1.122`, successful password authentication, a CyberHIVE shell prompt, and the remote CyberHIVE welcome surface. The server fingerprint displayed during connection is the same ED25519 fingerprint independently verified above.

The remote welcome correctly reports SSH auth mode `ephemeral-password`, host guard `pass`, and DevBridge/MCP/Remote Help `disabled`. It also prints `Pair/password hidden on remote terminals`, confirming that the local-console-only secret-display boundary is enforced for the remote session.

No SSH password or pairing code is persisted in this evidence record.

## Remaining verification boundary

The ephemeral hotfix proves the runtime repair path but does not prove that the repaired code is correctly embedded into a newly built image. The boot splash fix cannot be verified in the already-booted old image.

Therefore a new exact-head image build, USB rewrite and physical boot are still required to verify:

- automatic SSH readiness without manual repair;
- automatic browser readiness without manual repair;
- correct health semantics from first boot;
- branded UEFI boot splash.

## Current terminal state

`PHYSICAL_BOOT = PASS`

`RUNTIME_HOTFIX = PASS`

`LAN_HTTP_MDNS_SSH_REACHABILITY = PASS`

`SSH_INTERACTIVE_LOGIN = PASS`

`REMOTE_SECRET_DISPLAY_BOUNDARY = PASS`

`REPAIRED_IMAGE_ACCEPTANCE = PENDING_REBUILD`

`BOOT_SPLASH_REPAIR = PENDING_REBUILD`
