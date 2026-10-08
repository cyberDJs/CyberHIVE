# WB-HIVE-BOOT-0009 - CyberHIVE v0.3.1 Health Contract

## Status

Implementation prepared on an isolated branch. Not merged, not deployed and not written to USB.

## Approved scope

- introduce deterministic LOCAL_SAFE / CONNECTED / REMOTE_READY classification,
- remove Tailscale reachability from OTA candidate acceptance,
- add offline and Tailscale-outage tests,
- no Guardian repair actions,
- no partition/layout change,
- no USB write,
- no merge.

## Baseline

~~~
repository: cyberDJs/CyberHIVE
parent design commit: 3d2d2863c188155859e549c9056c00063122580a
boot baseline under design commit: 19668cd35ab6916bc0bead46a984eb5dd211c639
work branch: wb-hive-boot-0009-health-contract
~~~

## Contract

v0.3.1 keeps the existing v0.3 local service and persistence requirements but separates them from connectivity.

### LOCAL_SAFE

Passes only when:

- onboarding service is active,
- SSH service is active,
- local web service is active,
- mDNS service is active,
- host-disk guard is pass,
- usb-state persistence reports a validated mounted state.

LOCAL_SAFE does not require:

- LAN address,
- DNS,
- Tailscale backend Running,
- Tailscale IP,
- remote peer reachability.

OTA candidate acceptance uses LOCAL_SAFE.

### CONNECTED

Reports whether a non-Tailscale local IPv4 path is present.

CONNECTED does not participate in OTA candidate acceptance.

### REMOTE_READY

Passes only when:

- tailscaled service is active,
- Tailscale backend is Running,
- a Tailscale IPv4 address is present.

REMOTE_READY does not participate in OTA candidate acceptance.

## Compatibility

The existing top-level health schema remains:

~~~
cyberhive.live.health.v1
~~~

The existing top-level status field remains for compatibility:

- status=ok when LOCAL_SAFE passes,
- status=degraded when LOCAL_SAFE fails.

The new health object adds deterministic class output without requiring consumers to immediately migrate from the existing top-level fields.

## Test-first evidence

Before implementation both new tests were executed and failed for the intended missing behavior:

- test-cyberhive-health-classifier.py: classifier missing,
- test-cyberhive-offline-health-contract.py: health classifier integration missing.

After the minimal implementation both pass.

The inherited v0.2 and v0.3 validators and existing tests must also remain green.

## Explicitly out of scope

WB-HIVE-BOOT-0009 does not implement:

- Guardian restart/repair policy,
- network reconnect logic,
- setup AP,
- dedicated console service,
- general A/B boot-failure accounting,
- Recovery partition/runtime,
- repartitioning,
- image build,
- USB write,
- deployment,
- merge.

## Rollback

Code rollback is a normal branch revert to the WB-0008 parent because:

- no persistent schema migration is introduced,
- no GPT/partition layout changes,
- no bootloader format change,
- no secret state conversion.

A future physical image containing this change would still require its own separately approved rollback evidence.

## Verification

Required before readiness claim:

1. deterministic classifier behavior tests pass,
2. offline/Tailscale-outage contract test passes,
3. v0.2 inherited validator passes,
4. v0.3 validator passes,
5. existing v0.3 boot/pairing tests pass,
6. full Python suite passes,
7. git diff is limited to WB-0009 health contract, tests, CI and documentation,
8. no partition, GRUB layout or Guardian repair code changes.

## Stop line

~~~
Guardian repairs: NOT IMPLEMENTED
partition change: NO
image build: NO
USB write: NO
deployment: NO
merge: NO
~~~
