# Live Appliance v0.3 safety boundary

## Allowed persistent writes

Only the removable parent disk that contains `CYBER_EFI`, `CYBERHIVE_A`, `CYBERHIVE_B` and `CYBERHIVE_STATE` is an appliance persistence/update target. Persistent writes are limited to:

- `state/network/` - root-only NetworkManager profiles
- `state/tailscale/` - Tailscale machine state
- `state/ssh/` - SSH host keys and authorized public keys
- `state/ota/` - release, transaction, quarantine and rollback state
- `state/evidence/` - bounded non-secret health evidence
- `CYBERHIVE_A` and `CYBERHIVE_B` partitions - one active read-only live slot and one inactive OTA target
- the EFI `cyberhive/grubenv` boot-state file, only after matching-parent USB validation

## Forbidden

- raw runtime writes to `/dev/sd*`, NVMe, SATA or other host disks
- activating or writing host swap; live boot uses `noswap`
- writable EFI access before current-slot/STATE/EFI parent and USB transport checks
- persisting Wi-Fi passwords or Tailscale private state in Git
- storing the OTA release private signing key on CyberHIVE
- exposing SSH directly to the local LAN or internet by default
- treating LAN presence as management identity; local HTTP pairing still requires the physical console code
- accepting a signed DEV release whose sequence is not newer than both committed and quarantined sequence floors
- automatic bootloader replacement through the ordinary DEV channel
- treating successful download/build/write as runtime acceptance

## OTA verification and transaction order

GRUB resolves the slot partitions relative to the firmware-selected EFI device, rejects a visible duplicate selected-slot filesystem UUID and passes live-boot a selected-slot filesystem UUID device constraint. Runtime verification still rechecks that the live medium, EFI and STATE partitions share the same USB parent before writable access.

1. acquire the single OTA runtime lock
2. verify current slot, inactive slot, STATE and EFI resolve to one USB parent
3. fetch manifest and signature over HTTPS
4. verify SSHSIG namespace and dedicated signer identity
5. validate manifest schema/channel and monotonic release sequence against committed and failed/quarantined state
6. download bundle
7. verify exact bytes and SHA-256
8. validate exact archive path allowlist
9. install inactive slot
10. persist and sync complete pending metadata to `CYBERHIVE_STATE`
11. arm GRUB pending state on the matching EFI partition
12. reboot
13. candidate health gate runs
14. on PASS, write recoverable commit transaction and advance anti-downgrade state in STATE
15. only then clear pending boot state in EFI and finalize the transaction
16. on FAIL or detected rollback, quarantine the release before any automatic retry

If candidate persistence is unavailable, userspace does not attempt an unverified writable EFI mount. It requests a reboot so GRUB can return to the previous slot; the previous slot then reconciles stale pending STATE metadata and quarantines the rolled-back release.

## Host disk guard

The CyberHIVE device is identified by matching labels, a shared parent and `TRAN=usb`. It remains allowed when the kernel reports `RM=0`. Every other physical disk with a writable mounted filesystem is a guard violation.

## Secret handling

The repository contains public SSH keys only. First-boot Wi-Fi entry uses a no-echo local tty prompt. Support/evidence tooling must not read NetworkManager secrets, Tailscale state, SSH private host keys, pairing codes, passwords or the release signing private key.

## v0.3.1 health-gate security clarification

OTA acceptance is fail-closed on LOCAL_SAFE, not on external connectivity.

LOCAL_SAFE still requires the local management/security boundary to be healthy, including host-disk guard PASS, required local services and validated usb-state persistence. Tailscale service/backend/IP are reported under REMOTE_READY and are not proof that the local runtime is safe.

Loss of internet or Tailscale therefore cannot by itself cause a healthy candidate rollback. Conversely, self-healing is not allowed to disable the host-disk guard, open ordinary LAN SSH or weaken local pairing in order to regain REMOTE_READY.

WB-HIVE-BOOT-0009 adds classification and acceptance semantics only; it adds no automated Guardian repair actions.

## v0.3.1 Guardian repair boundary

WB-HIVE-BOOT-0010 extends allowed persistent writes with:

- state/guardian/state.json - root-only bounded retry/circuit metadata.

Guardian runtime evidence under /run/cyberhive/evidence/guardian.json is non-secret and ephemeral.

Before every automatic repair, Guardian reruns cyberhive-host-disk-guard. It also requires cyberhive-management-firewall.service to be active before restoring any local/network/remote service.

Guardian may only perform its explicit L0/L1 action allowlist. It must not reboot, power off, edit GRUB/EFI state, write A/B runtime slots, format/repartition media, enable LAN SSH, disable the management firewall, or change pairing/authentication policy.

Malformed Guardian persistent state is fail-closed and is not silently replaced, because silently resetting retry counters could bypass the circuit breaker.
