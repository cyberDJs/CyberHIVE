# WB-HIVE-BOOT-0008 - CyberHIVE v0.4 Appliance Guardian Design

## Status

Proposed / design-only.

## Work-block numbering reconciliation

The operator approval text named WB-HIVE-BOOT-0007.

Repository inspection on 2026-10-05 found that WB-HIVE-BOOT-0007 is already in use by:

~~~
branch: origin/wb-hive-boot-0007-grub-acer-repair
head: 19668cd35ab6916bc0bead46a984eb5dd211c639
purpose: Acer/GRUB parent-detection and physical validation repair
~~~

To preserve existing governance history, this design work is canonically recorded as WB-HIVE-BOOT-0008.

The renumbering does not expand the approved scope.

## Operator-approved scope

Approved request:

~~~
CYBERHIVE v0.4 APPLIANCE GUARDIAN
OFFLINE-SAFE PROVISIONING
GENERAL A/B SELF-HEAL DESIGN
WRITE ADR-0027 + FAILURE MATRIX + MIGRATION PLAN
NO IMPLEMENTATION
NO MERGE
NO USB WRITE
~~~

## Repository baseline

Design branch base:

~~~
repository: cyberDJs/CyberHIVE
branch base: origin/wb-hive-boot-0007-grub-acer-repair
base commit: 19668cd35ab6916bc0bead46a984eb5dd211c639
~~~

Additional physically relevant design input:

~~~
repair branch: repair-firstboot-autologin-v03
repair commit: b71fb9d6191f4c465b99da6a8a12fcfbe06c4a12
purpose: first-boot-only tty1 autologin repair
note: input only; not cherry-picked or merged by WB-HIVE-BOOT-0008
~~~

## Decision objective

Define an appliance architecture in which CyberHIVE:

- boots into a useful secure local state without internet,
- treats Tailscale as remote readiness rather than local boot correctness,
- heals bounded process/network failures automatically,
- does not enter infinite repair/reboot loops,
- fails over from a repeatedly failing committed slot to the other accepted slot,
- boots an independent Recovery runtime when both slots fail,
- preserves all existing host-disk and management security boundaries,
- has a deterministic v0.3 -> v0.4 migration and rollback path.

## Deliverables

1. docs/adr/ADR-0027-cyberhive-appliance-guardian-offline-safe-recovery.md
2. docs/architecture/live-appliance-v0-4-failure-matrix.md
3. docs/architecture/live-appliance-v0-4-migration-plan.md
4. this work-block scope/evidence record

## Key design decisions

- retain A/B + STATE + stable EFI trust foundation,
- split health into LOCAL_SAFE, CONNECTED and REMOTE_READY,
- make LOCAL_SAFE the OTA commit contract,
- replace shell/profile firstboot choreography with a dedicated console service,
- use resumable provisioning state,
- Ethernet first; setup AP only as bounded unprovisioned/recovery fallback,
- add one lightweight Guardian, not a new orchestration platform,
- define bounded repair ladder L0-L4,
- generalize A/B boot success accounting,
- add independent CYBER_RECOVERY,
- preserve tailnet-only SSH and physical local pairing,
- use hardware watchdog only when capability is proven,
- require v0.4 reflash/new media for partition/bootloader changes.

## Explicit non-goals

This work block does not:

- modify runtime code,
- modify GRUB code,
- add systemd units,
- add Recovery payloads,
- repartition media,
- build an image,
- write USB,
- boot hardware,
- deploy anything,
- merge anything,
- accept ADR-0027.

## Acceptance criteria

This work block is complete when:

- ADR-0027 is present and remains Proposed,
- failure matrix covers boot, STATE, provisioning, network, remote management, local control plane, OTA, watchdog, Recovery and security boundaries,
- migration plan separates OTA-compatible precursor work from reflash-required v0.4 layout work,
- rollback to untouched v0.3 media is defined,
- design explicitly states that Tailscale/internet are not part of LOCAL_SAFE,
- design preserves host-disk and management security boundaries,
- only documentation files changed,
- no merge, image build or USB write is performed.

## Recommended implementation sequence after future approval

1. v0.3.1 health-classification contract + tests,
2. Guardian state machine + bounded repair tests,
3. console/provisioning state machine,
4. network OOB/setup AP,
5. generalized GRUB boot-success contract,
6. Recovery image/layout,
7. migration tooling,
8. physical fault-injection campaign.

Each implementation work block must define its own exact source head, scope, tests and rollback.

## Stop line

~~~
WB-HIVE-BOOT-0008: DESIGN ONLY
implementation: NOT AUTHORIZED
merge: NOT AUTHORIZED
image build: NOT AUTHORIZED
USB write: NOT AUTHORIZED
deployment: NOT AUTHORIZED
ADR accepted: NO
~~~

## Headless bootstrap addendum

WB-HIVE-BOOT-0008 also defines optional read-only CYBERHIVE_CFG preseed as the zero-touch path for machines that have neither a usable Ethernet path nor an available physical display. This preserves headless-first operation without weakening pairing, firewall or host-disk boundaries.

~~~
CYBERHIVE_CFG preseed implementation: NOT AUTHORIZED
~~~
