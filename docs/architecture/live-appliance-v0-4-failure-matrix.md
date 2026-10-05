# CyberHIVE v0.4 Failure Matrix

Status: Proposed design evidence
Work block: WB-HIVE-BOOT-0008
Date: 2026-10-05

This matrix defines the failure-injection contract for the v0.4 Appliance Guardian architecture. It is not evidence that the behavior is implemented.

## Health classes

- **LOCAL_SAFE** - boot/storage/trust/local-control-plane contract.
- **CONNECTED** - at least one usable local network path.
- **REMOTE_READY** - Tailscale remote-management path operational.

Only LOCAL_SAFE is allowed to decide normal slot boot acceptance and OTA candidate commit.

## Repair escalation

| Level | Meaning | Typical action |
| --- | --- | --- |
| L0 | Process repair | Restart one failed daemon |
| L1 | Subsystem repair | Reconnect/reload networking or remote-management subsystem |
| L2 | Same-slot reboot | Reboot after bounded in-process repair failed |
| L3 | Alternate-slot failover | Boot the other accepted A/B slot |
| L4 | Recovery | Boot independent Recovery runtime |

Every automatic action requires a retry budget, cooldown, persistent reason code and evidence record.

## P0 boot and trust failures

| ID | Injection / condition | Detection | Expected automatic behavior | Escalation | Pass criterion |
| --- | --- | --- | --- | --- | --- |
| B01 | Normal boot with internet disconnected | health classifier | LOCAL_SAFE=pass, REMOTE_READY=fail/pending; no rollback | none | local console/web usable offline |
| B02 | DNS broken but LAN works | DNS/Tailscale probes | keep LOCAL_SAFE; retry remote asynchronously | L1 remote only | no reboot or slot rollback |
| B03 | Tailscale control plane unreachable | Tailscale state | keep candidate eligible if otherwise LOCAL_SAFE | L1 remote only | candidate commits without Tailscale |
| B04 | Current slot kernel/initrd missing | GRUB slot validation | mark slot boot failure and choose other accepted slot | L3 | alternate slot boots |
| B05 | Current slot squashfs/runtime invalid before userspace | GRUB/initramfs/runtime validation | failed boot remains uncommitted; next boot increments failure | L3 | alternate slot selected within budget |
| B06 | Current slot reaches userspace but never LOCAL_SAFE | boot-in-progress marker | bounded retry, then alternate slot | L2 -> L3 | no infinite reboot loop |
| B07 | Alternate slot also fails | per-slot counters | boot Recovery | L4 | Recovery UI boots |
| B08 | Recovery payload missing/corrupt | GRUB recovery validation | fail closed and show deterministic firmware/GRUB diagnostic | physical | no host-disk boot/write fallback |
| B09 | EFI parent cannot be proven | embedded GRUB proof | stop normal boot / diagnostic path | physical/recovery if provable | never constructs ambiguous (,gptN) slot path |
| B10 | Duplicate/ambiguous slot identity | boot/runtime identity checks | reject ambiguous slot | L3/L4 | no arbitrary device chosen |

## P0 STATE and persistence failures

| ID | Injection / condition | Detection | Expected automatic behavior | Escalation | Pass criterion |
| --- | --- | --- | --- | --- | --- |
| S01 | STATE missing | sibling-label/parent proof | normal runtime does not invent persistence elsewhere | L4 | Recovery boots |
| S02 | STATE mounts read-only unexpectedly | mount + write probe | record reason; no destructive remount tricks | L4 | Recovery offered |
| S03 | STATE filesystem inconsistent | mount/fs check | no auto-format; recovery-only repair flow | L4 | evidence preserved where possible |
| S04 | STATE 95% full | Guardian quota probe | purge only bounded cache/evidence eligible for deletion | L1 | boot/OTA journal untouched |
| S05 | STATE remains full after safe purge | Guardian | block new noncritical writes/OTA staging | operator | no boot-critical metadata loss |
| S06 | provisioning JSON truncated | schema parser | recover last atomic version or resume safe step | console/recovery | no secret leakage; no false complete |
| S07 | guardian journal malformed | schema parser | quarantine malformed guardian state and use conservative defaults | L1/L4 if boot-critical | no infinite action loop |
| S08 | migration journal interrupted | state migration transaction | resume or rollback migration deterministically | L4 | schema either old-valid or new-valid |

## P0 provisioning and local network failures

| ID | Injection / condition | Detection | Expected automatic behavior | Escalation | Pass criterion |
| --- | --- | --- | --- | --- | --- |
| N01 | Ethernet DHCP succeeds, Wi-Fi disconnected | NetworkManager | accept Ethernet, skip Wi-Fi prompt | none | provisioning continues |
| N02 | Ethernet carrier absent, saved Wi-Fi works | NetworkManager | connect saved Wi-Fi | none | CONNECTED=pass |
| N03 | No Ethernet and no saved Wi-Fi | network deadline | start ephemeral setup AP | local setup | phone can open local setup |
| N04 | Wrong Wi-Fi password | NM failure reason | remain in setup flow; do not loop credentials blindly | local setup | operator can retry another network |
| N05 | DHCP server unavailable | address probe | bounded reconnect; setup AP remains usable | L1 | no reboot loop |
| N06 | Wi-Fi disappears after provisioning | NM events | reconnect saved profile, then alternate saved profile | L1 | local runtime remains LOCAL_SAFE |
| N07 | NetworkManager crashes | systemd/Guardian | bounded service restart | L0/L1 | recovers without reboot if possible |
| N08 | Power cut after Wi-Fi save but before remote enrollment | provisioning state | resume at remote_access=pending | none | no repeated Wi-Fi entry |
| N09 | Power cut during provisioning state commit | atomic state transaction | previous complete state remains valid | console | no malformed complete marker |
| N10 | Setup AP exceeds allowed lifetime | Guardian timer | disable AP unless active local provisioning session | none | AP not left indefinitely exposed |

## P1 remote-management failures

| ID | Injection / condition | Detection | Expected automatic behavior | Escalation | Pass criterion |
| --- | --- | --- | --- | --- | --- |
| R01 | tailscaled process killed | systemd/Guardian | restart process | L0 | REMOTE_READY returns |
| R02 | Tailscale identity state unreadable | tailscaled/state error | do not regenerate silently; require recovery/re-enroll | operator/recovery | no identity split-brain |
| R03 | Tailscale backend stopped while LAN works | status probe | restart/retry with backoff | L0/L1 | no normal-slot rollback |
| R04 | SSH daemon killed | systemd/Guardian | bounded restart after config validation | L0 | only tailnet SSH restored |
| R05 | SSH config invalid | sshd -t | do not weaken auth; recovery/status reason | L1/operator | password/LAN fallback not enabled |
| R06 | firewall service fails | systemd/health | LOCAL_SAFE fails if management boundary cannot be enforced | L2/L3/L4 | no web/SSH exposure outside policy |
| R07 | remote repair retries exceed budget | circuit breaker | stop retrying until cooldown/state change | operator | no restart storm |

## P0/P1 local control-plane failures

| ID | Injection / condition | Detection | Expected automatic behavior | Escalation | Pass criterion |
| --- | --- | --- | --- | --- | --- |
| C01 | cyberhive-web killed | systemd/Guardian | restart | L0 | local UI returns |
| C02 | web repeatedly crashes | restart counter | circuit-breaker then same-slot reboot | L0 -> L2 | bounded attempts |
| C03 | Guardian killed | systemd | restart Guardian | L0 | no duplicate concurrent repair action |
| C04 | Guardian repeatedly crashes | systemd start limit | local services continue; boot evidence marks guardian degraded | L2/operator | no restart storm |
| C05 | host-disk guard returns violation | guard | fail closed; never auto-disable guard | operator/recovery | internal disk stays protected |
| C06 | local pairing code brute force | web rate limiter | rate limit across peers/session as defined | none | no auth bypass |
| C07 | pairing state lost on reboot | per-boot/session generation | generate new pairing session | none | old code/session invalid |

## P0 OTA and crash-consistency failures

| ID | Injection / condition | Detection | Expected automatic behavior | Escalation | Pass criterion |
| --- | --- | --- | --- | --- | --- |
| O01 | release manifest unavailable | updater | no-op/backoff | none | no reboot |
| O02 | signature invalid | verifier | reject release | none | no inactive-slot mutation |
| O03 | SHA/byte count mismatch | verifier | reject/quarantine download | none | no boot arm |
| O04 | power cut while downloading | partial staging | discard/resume safe cache only | none | current slot untouched |
| O05 | power cut writing inactive slot | incomplete stage metadata | inactive slot not armed | none | current slot boots |
| O06 | power cut after STATE pending journal sync, before EFI arm | journal reconciliation | clear/reconcile unarmed pending stage | none | no ambiguous candidate boot |
| O07 | power cut after EFI arm, before reboot | boot state | candidate gets governed attempt | candidate contract | deterministic |
| O08 | candidate reaches LOCAL_SAFE, internet unavailable | local health | commit candidate | none | no false rollback |
| O09 | candidate fails LOCAL_SAFE | health gate | quarantine + rollback | L3 | previous accepted slot boots |
| O10 | power cut during commit transaction | recovery transaction | finalize or restore on next boot | L3/L4 | no split-brain release state |
| O11 | failed candidate is offered again | quarantine floor | reject same/lower sequence | none | no reinstall loop |
| O12 | ordinary OTA attempts Recovery/EFI replacement | updater allowlist | reject | none | boot/recovery immutable under ordinary channel |

## P1 hardware/watchdog failures

| ID | Injection / condition | Detection | Expected automatic behavior | Escalation | Pass criterion |
| --- | --- | --- | --- | --- | --- |
| H01 | hardware watchdog available | capability probe | Guardian/systemd feeds watchdog only while alive | hardware reset | tested timeout reset |
| H02 | no hardware watchdog | capability probe | record unsupported; no false self-heal claim | none | status accurately reports limitation |
| H03 | userspace deadlock | watchdog timeout | hardware reset when supported | reboot -> boot accounting | next boot sees unfinished attempt |
| H04 | USB transient I/O errors | kernel/journal probes | stop writes, preserve evidence if possible | L2/L3/L4 | no blind repeated writes |
| H05 | USB physically removed | device disappearance | fail closed; no host-disk substitution | physical | no writes redirected elsewhere |
| H06 | physical USB failure | device I/O failure | cannot self-heal from same medium | physical | explicit limitation reported |

## P1 Recovery failures and safety

| ID | Injection / condition | Detection | Expected automatic behavior | Escalation | Pass criterion |
| --- | --- | --- | --- | --- | --- |
| Q01 | Recovery boots with STATE absent | recovery init | start local diagnostics/setup without STATE dependency | none | Recovery usable |
| Q02 | Recovery sees internal host disks | device inventory | read-only inventory only | none | no writes |
| Q03 | Recovery filesystem check requested | physical authenticated action | operate only on validated USB STATE while unmounted | operator | exact target proof |
| Q04 | Recovery slot restore requested | signed bundle verifier | restore only selected CyberHIVE A/B partition | operator | signature/hash/parent checks |
| Q05 | unsigned recovery payload | verifier | reject | none | no bypass |
| Q06 | setup AP in Recovery | recovery network | ephemeral auth + local pairing | none | no ordinary LAN SSH |

## Evidence requirements

Each automated failure test must capture, when applicable:

- exact source commit,
- image manifest + SHA-256,
- boot slot and release ID,
- boot-attempt/failure counters,
- STATE schema/version,
- Guardian reason code and repair level,
- systemd state,
- LOCAL_SAFE, CONNECTED, REMOTE_READY,
- host-disk guard result,
- GRUB environment before/after,
- whether reboot/failover/Recovery occurred,
- explicit negative claims for host-disk writes and auth weakening.

Secrets must be redacted.

## Required implementation test tiers

### Tier 1 - deterministic unit/contract tests

Required for:

- state transitions,
- retry budgets,
- schema validation,
- health classification,
- GRUB decision interpreter,
- migration transactions,
- updater allowlists.

### Tier 2 - VM fault injection

Required for:

- process crashes,
- network loss,
- power-cut simulation around file transactions,
- slot failure,
- dual-slot failure,
- Recovery selection.

### Tier 3 - physical USB/hardware

Required for:

- firmware/GRUB parent discovery,
- actual A/B boot,
- actual Recovery boot,
- USB unplug/I/O behavior,
- Wi-Fi setup AP,
- hardware watchdog,
- exact media-write/readback evidence.

## Promotion gate

v0.4 is not eligible for physical promotion until every P0 row has:

- an automated reproducer where technically possible,
- a documented expected state transition,
- a passing result,
- no unbounded retry,
- a rollback/recovery path.

## Stop line

~~~
failure matrix: DESIGN ONLY
failure injections executed: NO
implementation: NOT AUTHORIZED
merge: NOT AUTHORIZED
USB write: NOT AUTHORIZED
~~~

## Additional headless/preseed failure cases

| ID | Injection / condition | Detection | Expected automatic behavior | Escalation | Pass criterion |
| --- | --- | --- | --- | --- | --- |
| N11 | Headless boot with valid read-only CYBERHIVE_CFG | config-media validator | import only allowlisted bootstrap state and continue provisioning | none | no monitor required |
| N12 | CYBERHIVE_CFG malformed, writable or expired | config-media validator | reject preseed and fall back to interactive/local-safe path | local setup | no secret/config bypass |

### Addendum stop line

~~~
headless/preseed cases: DESIGN ONLY
implementation: NOT AUTHORIZED
merge: NOT AUTHORIZED
USB write: NOT AUTHORIZED
~~~
