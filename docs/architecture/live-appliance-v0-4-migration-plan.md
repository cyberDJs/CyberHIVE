# CyberHIVE v0.3 -> v0.4 Migration Plan

Status: Proposed / design-only
Work block: WB-HIVE-BOOT-0008
Date: 2026-10-05

## Goal

Move a proven v0.3 single-USB A/B appliance to the v0.4 Appliance Guardian architecture while preserving a deterministic rollback path and without using ordinary OTA to repartition the currently booted USB.

## Source baselines

Design baseline:

~~~
boot branch: origin/wb-hive-boot-0007-grub-acer-repair
commit: 19668cd35ab6916bc0bead46a984eb5dd211c639
~~~

Parallel validated firstboot repair input:

~~~
branch: repair-firstboot-autologin-v03
commit: b71fb9d6191f4c465b99da6a8a12fcfbe06c4a12
status: physically relevant repair input, not merged by this work block
~~~

WB-HIVE-BOOT-0008 is documentation only.

## Migration principles

1. Do not repartition the active v0.3 USB through ordinary OTA.
2. Prefer a second USB for v0.4 so the complete v0.3 medium remains the rollback asset.
3. Import only allowlisted state.
4. Default to new remote machine identity unless the operator deliberately chooses identity preservation.
5. Never copy secrets into Git, chat, support bundles or unencrypted temporary files.
6. A failed v0.4 migration must leave the v0.3 medium untouched and bootable.
7. Do not write host internal disks as part of migration.

## Compatibility split

### v0.3.1 software-only precursor

The following architecture pieces are compatible with the existing v0.3 partition layout and MAY later be delivered as a normal signed runtime update after separate implementation approval:

- health split: LOCAL_SAFE, CONNECTED, REMOTE_READY,
- remove Tailscale from OTA candidate acceptance,
- Guardian service and bounded repair policies,
- resumable provisioning state schema,
- dedicated console service,
- Ethernet-first network behavior,
- bounded STATE cache/evidence cleanup,
- stable local device ID,
- software watchdog integration hooks,
- new evidence/reason-code schema.

The following MUST NOT be attempted by ordinary v0.3 OTA:

- adding CYBER_RECOVERY,
- repartitioning the USB,
- replacing the bootloader contract,
- changing GPT partition numbering,
- destructive STATE filesystem changes.

### v0.4 media migration

Required for:

- Recovery partition,
- generalized A/B boot-failure accounting in GRUB,
- new partition numbering/layout,
- any bootloader-format change required by the recovery contract.

## Recommended migration: second USB

This is the default path.

### Phase 0 - freeze source and evidence

Before build:

- record exact implementation source commit,
- run all v0.4 P0 automated gates,
- produce image manifest and hashes,
- record supported hardware/media minimums,
- verify Recovery payload is present,
- verify ordinary OTA cannot modify Recovery/EFI.

No media write occurs until separately approved.

### Phase 1 - create v0.4 media

Write the verified v0.4 image to a second known removable USB.

Required evidence:

- exact removable target identity,
- image SHA-256,
- raw readback verification,
- GPT labels/order,
- EFI/Recovery/A/B/STATE integrity.

The old v0.3 USB remains untouched.

### Phase 2 - first v0.4 boot in isolated migration mode

Boot v0.4 with the old v0.3 USB disconnected or connected only as an explicitly selected read-only migration source.

v0.4 must first prove:

- its own EFI/slot/STATE parent,
- LOCAL_SAFE,
- host-disk guard,
- Recovery availability,
- migration mode reason code.

### Phase 3 - import allowlisted state

Default import policy:

| State | Default | Reason |
| --- | --- | --- |
| Wi-Fi NetworkManager profiles | import allowed | reduces setup friction; secrets remain local |
| owner authorized_keys | import allowed | public keys only |
| stable non-secret device ID | import allowed if collision-safe | continuity |
| role intent | import allowed | non-secret |
| OTA quarantine/current sequence metadata | import selectively after schema conversion | prevents downgrade/retry regression |
| evidence history | optional bounded import | diagnostics only |
| Tailscale machine state | **do not clone by default** | avoids duplicate machine identity |
| SSH host private keys | **do not clone by default** | avoids duplicate host identity with rollback medium |
| pairing/session codes | never import | session-bound |
| cache | never import | disposable |

Default behavior therefore re-enrolls Tailscale and generates a new SSH host identity on v0.4.

This makes the untouched v0.3 USB safe to boot as rollback without two media sharing the same remote/SSH private identity.

### Optional identity-preserving import

Identity preservation is an explicit advanced migration mode.

It may import:

- Tailscale machine state,
- SSH host private keys,

only when:

1. the old v0.3 media is powered off,
2. the operator accepts that both media represent the same logical machine identity,
3. the old media is marked sealed/offline until rollback is intentionally selected,
4. import occurs only from a validated CyberHIVE USB source,
5. private state never passes through plaintext chat/log/evidence surfaces.

The implementation must prevent casual simultaneous activation of cloned identities.

### Phase 4 - remote re-enrollment

Default migration:

1. bring up Ethernet/saved Wi-Fi/setup AP,
2. finish local provisioning,
3. enroll the new v0.4 node into Tailscale,
4. verify displayed SSH host fingerprint,
5. verify tailnet-only SSH,
6. verify local browser pairing fallback.

Remote enrollment failure does not invalidate LOCAL_SAFE.

### Phase 5 - prove self-healing

Before retiring v0.3 media, run the migration acceptance subset:

- cold boot offline,
- Ethernet-only boot,
- Tailscale outage,
- web restart recovery,
- current-slot forced failure -> alternate slot,
- alternate-slot forced failure -> Recovery,
- Recovery local UI,
- host-disk guard fail-closed,
- reboot after clean shutdown,
- support/evidence export.

### Phase 6 - hold rollback asset

Keep the v0.3 USB unchanged for a defined soak period.

Recommended initial soak:

~~~
minimum: 7 days
preferred: 14 days including at least 3 cold boots
~~~

Do not erase the old medium until:

- v0.4 acceptance passes,
- no unresolved P0/P1 boot issue exists,
- remote management is stable,
- operator explicitly retires the old rollback medium.

## Single-USB fallback migration

If only one USB exists, the safe preference is fresh re-provisioning after verified reflash.

Before reflash, export only what is necessary to a trusted operator-controlled computer or second removable medium.

The migration export feature, if implemented, must:

- use an explicit operator action,
- create an encrypted bundle for any secrets,
- include a manifest and integrity hash,
- never upload automatically,
- never write internal host disks without the operator choosing that destination,
- distinguish public/non-secret export from secret state.

A single-USB reflash has a weaker rollback story and therefore requires a separately explicit media-write approval.

## STATE schema migration

v0.4 STATE migration uses an atomic transaction.

Conceptual files:

~~~
state/schema-version
state/migration/current.json
state/migration/last-success.json
~~~

Algorithm:

1. validate existing schema,
2. create migration journal with source/target versions,
3. copy/transform allowlisted state into new paths,
4. fsync/sync new files,
5. validate target schema,
6. atomically advance schema-version,
7. mark migration committed,
8. only then clean obsolete non-secret state.

Power loss before step 6 leaves the old schema authoritative.

Power loss after step 6 resumes cleanup but must not roll back secrets to an ambiguous version.

Migration does not automatically repair a filesystem that fails integrity checks; that moves to Recovery.

## Boot state migration

Do not reuse arbitrary v0.3 grubenv fields blindly.

The v0.4 image starts with a known-clean boot-state schema.

Imported persistent metadata MAY initialize:

- prior accepted release ID/sequence,
- prior quarantine floor,
- role/device intent.

v0.4 boot-failure counters start clean after the new media passes its first LOCAL_SAFE.

## OTA metadata migration

To preserve anti-downgrade behavior:

- import only well-formed numeric committed/quarantined sequence floors,
- import release IDs only when paired with valid sequence state,
- malformed metadata is not guessed or silently normalized,
- conflicting metadata requires operator/recovery review.

## Rollback

### Before v0.3 medium retirement

Rollback is:

1. power off v0.4,
2. disconnect v0.4 USB,
3. boot the untouched v0.3 USB,
4. verify its normal v0.3 health.

If default fresh Tailscale/SSH identities were used on v0.4, v0.3 retains its old identities and can resume remote management normally.

### After v0.3 medium retirement

Rollback requires a verified archived v0.3 image and an explicitly approved media write. This is weaker than retaining the original medium during soak.

## Failure conditions that stop migration

Stop and return to v0.3 if any of these occur:

- v0.4 cannot prove its boot USB parent,
- Recovery does not boot,
- host-disk guard is not PASS,
- both A/B slots are not verifiably present,
- STATE schema migration is ambiguous,
- ordinary OTA can mutate Recovery/EFI,
- setup AP bypasses local authorization,
- A/B failover loops,
- evidence cannot distinguish local health from remote connectivity.

## Migration acceptance criteria

A migration is accepted only when:

- v0.4 exact source and image hashes are recorded,
- raw USB readback passes,
- LOCAL_SAFE passes offline,
- first/local provisioning is resumable,
- Tailscale is not part of slot acceptance,
- A/B general failover is demonstrated,
- Recovery is demonstrated independently of STATE,
- no internal host disk write occurred,
- the old v0.3 rollback medium remains available through the soak period.

## Stop line

~~~
migration plan: DESIGN ONLY
migration executed: NO
implementation: NOT AUTHORIZED
merge: NOT AUTHORIZED
USB write: NOT AUTHORIZED
old v0.3 media mutation: NOT AUTHORIZED
~~~
