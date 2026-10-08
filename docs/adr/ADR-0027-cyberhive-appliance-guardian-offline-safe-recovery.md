# ADR-0027 - CyberHIVE Appliance Guardian, Offline-Safe Provisioning and General A/B Self-Healing

Status: Proposed
Date: 2026-10-05
Owners: CyberDJs / CyberHIVE maintainers

## Context

CyberHIVE v0.3 established the correct core storage and update model for an unattended single-USB appliance:

- stable UEFI boot partition,
- A/B runtime slots,
- persistent STATE journal,
- signed inactive-slot OTA,
- one-attempt candidate boot,
- candidate health commit or rollback,
- release quarantine after failed rollout,
- persistent Wi-Fi, Tailscale, SSH identity and bounded evidence,
- Tailscale-only SSH,
- LAN HTTP pairing without treating LAN presence as identity,
- host-disk write guards.

The v0.3 architecture is retained as the trust foundation rather than replaced.

Current v0.3 health and provisioning still couple local appliance correctness to external connectivity. The candidate boot health gate requires Tailscale to be Running. First boot is a tty1 login/autologin/profile chain that launches a shell script. Service healing is mostly delegated to individual systemd restart behavior. A/B rollback primarily protects pending OTA candidates and does not provide a general response to a previously committed slot becoming unbootable. There is no independent recovery runtime and no coordinated appliance-level repair ladder.

Physical validation also proved that firmware-specific bootloader parent discovery must be treated as a first-class boot invariant. The Acer-class UEFI repair branch at 19668cd35ab6916bc0bead46a984eb5dd211c639 records those invariants. The independently verified first-boot-only tty1 repair at b71fb9d6191f4c465b99da6a8a12fcfbe06c4a12 is a parallel input to this decision and is not merged by this work block.

This ADR defines the v0.4 target architecture. It is design-only. It does not authorize implementation, merge, deployment, partition changes or USB writes.

## Decision drivers

1. A healthy local appliance must remain useful without internet, DNS or Tailscale.
2. Ordinary process, network and remote-management failures should recover automatically without boot-looping.
3. A previously committed slot that later fails must be able to fall back to the other known-good slot.
4. Both runtime slots failing must lead to an independent local recovery environment.
5. Automatic repair must never weaken the host-disk, identity or management security boundaries.
6. Recovery actions must be bounded, observable and protected from infinite retry loops.
7. The design must remain a single-node modular appliance, not introduce Kubernetes, a distributed database or another mandatory control plane.
8. v0.3 media must have a deterministic migration and rollback story.

## Constraints

- Local-first and useful offline.
- LAN presence is not management identity.
- SSH remains unavailable directly on the ordinary LAN by default.
- Ordinary OTA must not repartition the USB or replace the bootloader.
- Host internal disks remain outside the default persistence/update boundary.
- The appliance may run on hardware without a usable hardware watchdog.
- Physical failure of the only USB cannot be healed by software stored on that same failed USB.
- Recovery must not automatically format STATE or host disks.
- Release signing private keys are never stored on the appliance.

## Considered options

### Option A - Keep v0.3 and add more systemd restart policies

Rejected. This does not solve offline health classification, resumable provisioning, general A/B failover, dual-slot failure, STATE recovery or coordinated repair.

### Option B - Replace the live appliance with a mutable installed Linux system

Rejected. A mutable root weakens rollback determinism, increases drift and removes the simple A/B trust model already proven by v0.3.

### Option C - Add a container orchestrator or distributed supervisor

Rejected. The single-node appliance does not need Kubernetes, consensus or a separate database to recover NetworkManager, Tailscale or the web service.

### Option D - Extend v0.3 into an appliance-level Guardian architecture

Accepted. Keep A/B + STATE + stable EFI, but separate local health from connectivity, add bounded repair, make provisioning resumable, generalize boot-success accounting and add independent Recovery.

## Decision

CyberHIVE v0.4 SHALL use the following architecture.

### 1. Three health classes

The single ok/degraded interpretation is replaced by three independent health classes.

#### LOCAL_SAFE

LOCAL_SAFE is the boot and OTA acceptance contract.

Minimum requirements:

- firmware selected a valid CyberHIVE EFI parent,
- booted slot identity matches the declared slot,
- current runtime slot contents are internally valid,
- STATE is either mounted from the validated sibling partition or the runtime is deliberately in Recovery,
- host-disk guard passes,
- local control plane is running,
- local console/status surface is running,
- required persistent-state schema is readable and not known corrupt,
- no unresolved boot-critical transaction exists.

LOCAL_SAFE MUST NOT require:

- internet access,
- working DNS,
- a Tailscale control-plane connection,
- a Tailscale IP,
- external release infrastructure,
- any remote peer.

A candidate release is committed when LOCAL_SAFE passes, not when remote connectivity passes.

#### CONNECTED

CONNECTED reports whether at least one useful local network path is operational, for example Ethernet, Wi-Fi or setup/recovery AP. Failure of CONNECTED does not make a locally healthy appliance unbootable.

#### REMOTE_READY

REMOTE_READY reports remote-management readiness: tailscaled active, backend Running, Tailscale address present and remote-management firewall contract active. Failure is repaired asynchronously and does not trigger OTA rollback by itself.

### 2. Dedicated local console service

The v0.4 first-boot path SHALL no longer depend on:

~~~
getty -> autologin -> interactive shell -> profile.d -> sudo firstboot
~~~

A dedicated root-owned cyberhive-console.service SHALL own the physical console during provisioning and recovery.

Responsibilities:

- display boot slot, release and health classes,
- display hardware/network state without secrets,
- drive first-boot provisioning,
- display pairing/setup QR material,
- show Tailscale enrollment state,
- expose a constrained recovery menu,
- never provide an unrestricted root shell as the default UI.

After provisioning, the console becomes a status/recovery surface. An administrative shell, if retained, is an explicit physical recovery action.

### 3. Resumable provisioning state machine

Provisioning becomes an explicit persistent state machine stored in STATE.

Example logical state:

~~~json
{
  "schema": "cyberhive.provisioning.v1",
  "device_identity": "done",
  "owner_key": "done",
  "local_network": "done",
  "remote_access": "pending",
  "complete_local": true
}
~~~

Rules:

- every step is atomic and idempotent,
- power loss resumes from the last committed step,
- local provisioning can complete without internet,
- Tailscale enrollment can remain pending,
- credentials are never written to evidence or logs,
- provisioning state is schema-versioned.

The old state/provisioned marker MAY remain temporarily as migration compatibility, but is not the v0.4 source of truth.

### 4. Out-of-box network policy

Network setup follows this order:

1. use Ethernet automatically when carrier + DHCP produce a usable address,
2. otherwise use previously persisted Wi-Fi profiles,
3. otherwise, when unprovisioned or explicitly in Recovery, create an ephemeral setup AP,
4. allow local web provisioning through the setup AP,
5. disable the setup AP after a normal network path is established.

The setup AP:

- exists only in unprovisioned/recovery states,
- uses an ephemeral WPA2/WPA3 credential shown only on the physical console/QR,
- does not enable ordinary LAN SSH,
- does not treat association as management identity,
- requires the local pairing/setup token for mutations,
- is rate-limited and time-bounded,
- is disabled when provisioning succeeds.

Ethernet MUST NOT cause a Wi-Fi prompt merely because no Wi-Fi interface is connected.

### 5. Appliance Guardian

Add one small local cyberhive-guardian supervisor. It coordinates cross-component state; systemd remains the process supervisor.

The Guardian SHALL:

- evaluate health classes,
- consume systemd and component status,
- run bounded repairs,
- record repair evidence,
- enforce backoff and circuit breakers,
- request reboot/failover/recovery only after lower repair levels are exhausted,
- never bypass trust or authentication controls.

The Guardian MUST NOT:

- maintain a separate distributed state store,
- format STATE automatically,
- write host internal disks,
- disable the host-disk guard,
- open SSH on the ordinary LAN,
- retry forever.

### 6. Repair ladder

Automatic repair SHALL use explicit escalation levels.

- L0 process repair: restart one failed daemon.
- L1 subsystem repair: reconnect/reload networking or remote-management subsystem.
- L2 same-slot reboot: bounded reboot after in-process repair fails.
- L3 alternate-slot failover: boot the other accepted A/B slot.
- L4 Recovery: boot independent Recovery runtime.

Every level has a retry budget, time window, cooldown, persistent reason code and deterministic escalation target.

### 7. General A/B boot-success contract

A/B becomes a general runtime resilience mechanism, not only an OTA candidate mechanism.

EFI boot state SHALL track enough information to detect a boot that never reached LOCAL_SAFE, conceptually including:

- selected/current slot,
- last known-good slot,
- boot-in-progress marker,
- bounded per-slot failure counters,
- recovery request,
- OTA pending candidate when applicable.

Before entering a normal slot, GRUB marks the boot attempt in progress.

After LOCAL_SAFE, userspace records boot success for boot/OTA acceptance, but that record MUST NOT be the only signal used to judge later slot health. v0.4 SHALL also maintain an independently detectable runtime marker, clean-shutdown marker or equivalent persistent signal that survives watchdog reset, kernel panic, deadlock or unclean reboot after LOCAL_SAFE.

A normal shutdown clears the runtime marker or records a clean stop. A watchdog reset, power loss, panic or repeated userspace crash after LOCAL_SAFE leaves an unfinished runtime attempt that the next boot can attribute to the same slot.

If the next firmware boot observes an unfinished previous boot attempt before LOCAL_SAFE, that slot accrues a boot failure. If userspace observes an unfinished post-LOCAL_SAFE runtime marker from the previous boot, that slot accrues a post-acceptance runtime failure and the same bounded L2 -> L3 -> L4 escalation policy applies.

After the configured failure threshold, GRUB selects the other eligible accepted slot.

If neither normal slot is eligible, GRUB selects Recovery.

Implementation must minimize EFI writes and prove crash consistency. This ADR does not freeze exact grubenv field encoding or the exact runtime-marker storage format.

### 8. Unify OTA candidate and normal boot accounting

v0.4 SHOULD avoid two independent retry state machines for normal-slot failures and OTA candidate failures.

OTA remains stricter: signed metadata, inactive-slot install, one candidate acceptance attempt unless explicitly revised and quarantine after failure. The underlying boot-attempt accounting should use the same boot-success contract.

STATE remains authoritative for release metadata and OTA transactions. EFI remains minimal boot-selection state.

### 9. Independent Recovery runtime

v0.4 media SHALL add a read-only CYBER_RECOVERY partition/runtime.

Logical layout:

~~~
GPT1  CYBER_EFI
GPT2  CYBER_RECOVERY
GPT3  CYBERHIVE_A
GPT4  CYBERHIVE_B
GPT5  CYBERHIVE_STATE
tail  reserved/unallocated for future explicit data use
~~~

Exact partition sizes are not frozen by this ADR. Implementation must prove:

- each runtime partition has at least 30% free headroom after build,
- Recovery fits with required tools,
- minimum supported media size is documented,
- raw image size remains operationally acceptable.

Recovery must boot without requiring normal STATE to be healthy.

Recovery capabilities:

- inspect/verify A and B,
- inspect GRUB state,
- run read-only diagnostics,
- run explicit filesystem checks against STATE when unmounted,
- restore a slot from an already verified signed bundle,
- normalize boot selection,
- export a support bundle,
- expose setup AP/local pairing,
- permit deliberate re-provisioning.

Recovery MUST NOT automatically format STATE, erase runtime slots, write host internal disks, accept unsigned repair payloads or expose unauthenticated remote administration.

Recovery slot restore MUST enforce the signed release metadata sequence floor and the failed-release quarantine floor retained from v0.3. A correctly signed but older, replayed or quarantined bundle is rejected by default unless a separately authenticated explicit downgrade override is later designed and approved.

Ordinary OTA MUST NOT replace Recovery or the bootloader. Updating Recovery is a separately governed maintenance operation.

### 10. Persistent STATE schema

STATE becomes explicitly schema-versioned.

Minimum namespaces:

~~~
state/device/
state/provisioning/
state/network/
state/tailscale/
state/ssh/
state/ota/
state/guardian/
state/boot/
state/evidence/
cache/
~~~

Requirements:

- atomic file replacement for boot-critical metadata,
- fsync/sync at transaction boundaries,
- bounded evidence retention,
- bounded cache retention,
- schema version + migration journal,
- no secret values in ordinary evidence,
- filesystem-low-space thresholds,
- no automatic destructive repair.

If STATE becomes read-only or fails integrity checks, normal runtime enters degraded/recovery escalation rather than silently creating replacement state elsewhere.

### 11. Device identity

v0.4 SHALL create a stable local device identifier in STATE, independent of IP, Tailscale IP, current slot and boot session. It is not itself an authentication secret.

SSH host identity and Tailscale machine identity remain protected secrets with explicit migration policies.

### 12. Hardware watchdog

When supported by hardware, systemd hardware watchdog integration SHOULD be enabled with a conservative timeout determined during hardware validation.

The Guardian is watchdog-aware. If no hardware watchdog exists, CyberHIVE records that limitation and does not claim hard-reset self-healing.

### 13. Local services are not ordered behind internet readiness

Boot-critical local services SHALL not require external connectivity to become available.

network-online.target MAY be used for components that genuinely require a configured local interface, but local console, persistence validation, host-disk guard and local health remain independent of internet/Tailscale.

Remote readiness is asynchronous.

### 14. Security boundary is preserved

v0.4 keeps the v0.3 security rules:

- LAN presence is not identity,
- root SSH login disabled,
- ordinary LAN SSH denied,
- tailnet SSH only,
- local HTTP mutations require physical pairing/setup authorization,
- host-disk guard remains fail-closed,
- release signatures remain mandatory,
- signing private keys remain off-device,
- Recovery does not silently weaken management policy.

Self-healing may restore a failed security control only to its declared secure configuration. It may not disable the control to regain availability.

## Consequences

### Positive

- internet loss no longer causes a healthy OTA candidate to roll back,
- a working Ethernet path no longer forces Wi-Fi setup,
- provisioning survives power loss,
- process/network failures gain bounded automatic repair,
- committed-slot corruption can fail over to the other accepted slot,
- post-LOCAL_SAFE runtime crashes can be detected and escalated instead of looping forever,
- dual-slot failure has a deterministic Recovery destination,
- operators gain a single local status/recovery surface,
- appliance remains useful offline,
- troubleshooting evidence becomes structured around reason codes and repair levels.

### Negative

- boot state becomes more complex,
- Recovery adds build size and a new maintenance lifecycle,
- generalized slot failover requires careful GRUB crash-consistency testing,
- setup AP adds a temporary wireless attack surface,
- watchdog behavior is hardware-dependent,
- migration from v0.3 to v0.4 requires reflash/new media because partition layout changes.

## Security impact

The design slightly expands local attack surface through setup AP and Recovery UI. Those surfaces are accepted only with physical-console-disclosed ephemeral credentials, local pairing tokens, rate limits, no LAN SSH, time-bounded setup mode and strict recovery write allowlists.

The design reduces risk from ad-hoc emergency fixes because recovery and repair paths become explicit and governed.

## Performance and resource impact

Expected steady-state overhead on the reference x86_64 / 32 GB RAM appliance is small:

- one lightweight Guardian process,
- periodic local probes,
- bounded evidence writes,
- no additional database,
- no distributed consensus,
- no mandatory containers.

Guardian probing should be event-driven where practical and rate-limited otherwise. It must not materially affect inference CPU/GPU scheduling.

## Rejected alternatives

- full mutable root persistence,
- in-place active-slot updates,
- unbounded restart loops,
- automatic STATE formatting,
- SSH LAN recovery fallback,
- mandatory cloud health service,
- mandatory Kubernetes,
- treating Tailscale reachability as release acceptance,
- reusing a normal runtime slot as the only Recovery environment.

## Validation

ADR acceptance requires the associated failure matrix to pass at its required evidence level.

Minimum P0 validation:

1. boot succeeds with no internet,
2. Ethernet-only first boot does not request Wi-Fi,
3. power interruption during provisioning resumes correctly,
4. Tailscale outage does not invalidate LOCAL_SAFE,
5. web and tailscaled process failures heal within retry budget,
6. current-slot repeated boot failure selects alternate slot,
7. post-LOCAL_SAFE crash, deadlock or unclean reboot is recorded by an independent runtime/clean-shutdown marker and cannot loop forever in the same slot,
8. both normal slots failing selects Recovery,
9. STATE read-only/corrupt condition reaches Recovery without auto-format,
10. power interruption at each OTA transaction boundary has deterministic outcome,
11. host-disk guard failure never triggers a repair that weakens the guard,
12. setup AP requires ephemeral local authorization,
13. Recovery cannot write host internal disks,
14. Recovery restore rejects older, replayed or quarantined bundles unless a separately authenticated downgrade override is explicitly approved.

## Migration / rollback

Migration is defined in docs/architecture/live-appliance-v0-4-migration-plan.md.

Ordinary OTA may deliver software-only precursors, but adding CYBER_RECOVERY and changing the bootloader contract requires a separately approved v0.4 media migration. v0.3 must not repartition its own active USB through the ordinary OTA channel.

Rollback from initial v0.4 migration is the untouched v0.3 USB/media or a verified v0.3 image. v0.4 migration should therefore prefer a second USB so the original remains an immediate rollback asset.

## Related decisions

- ADR-0026 - CyberHIVE unattended single-USB A/B OTA.
- Existing v0.3 host-disk, signing and identity boundaries remain applicable unless explicitly superseded here.

If accepted and implemented, ADR-0027 supersedes ADR-0026 only for health classification, boot-success/failure accounting, Recovery partition/layout and provisioning lifecycle.

ADR-0026 remains the source for the signed OTA transaction model unless later superseded.

## Review date

Review after the v0.4 failure-injection prototype completes and before authorizing any v0.4 USB write.

## Unresolved implementation questions

1. exact GRUB environment encoding and minimal-write algorithm,
2. exact Recovery partition size,
3. exact per-slot boot-failure threshold,
4. hardware watchdog support matrix,
5. whether setup AP is available on every supported Wi-Fi chipset,
6. exact STATE filesystem check/repair policy,
7. whether optional preseed configuration includes an ephemeral Tailscale auth key,
8. long-term policy for unused media tail / future CYBERHIVE_DATA.

## Stop line

~~~
ADR status: PROPOSED
implementation: NOT AUTHORIZED
merge: NOT AUTHORIZED
USB write: NOT AUTHORIZED
deployment: NOT AUTHORIZED
partition migration: NOT AUTHORIZED
~~~

## Design addendum - Headless zero-touch bootstrap

CyberHIVE remains headless-first. A machine with working Ethernet can reach local provisioning without Wi-Fi setup, but a fully headless machine with no usable network path cannot depend on a credential displayed only on a monitor.

v0.4 SHALL therefore support an optional physical preseed path using a separately attached read-only CYBERHIVE_CFG medium.

The preseed format is schema-versioned and strictly allowlisted. It MAY contain:

- owner SSH public keys,
- one or more NetworkManager connection profiles,
- role/device intent,
- a one-time local setup bootstrap token,
- an optional short-lived, scoped Tailscale enrollment credential when explicitly provisioned by the operator.

Rules:

- config media is mounted read-only with nodev,nosuid,noexec,
- malformed or writable config media is rejected,
- secrets are consumed into validated STATE only when needed and never copied to ordinary evidence,
- a Tailscale enrollment credential must be short-lived/scoped and is not retained after machine state is established,
- absence or expiry of remote enrollment material does not block LOCAL_SAFE,
- preseed never authorizes host-disk writes or weakens pairing/firewall policy.

Interactive console/setup-AP provisioning remains the default human path. CYBERHIVE_CFG is the zero-touch/headless path, not a mandatory dependency.

### Addendum stop line

~~~
headless preseed: DESIGN ONLY
implementation: NOT AUTHORIZED
merge: NOT AUTHORIZED
USB write: NOT AUTHORIZED
~~~
