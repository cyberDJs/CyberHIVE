# WB-HIVE-BOOT-0010 - CyberHIVE Guardian bounded L0/L1 repair

## Status

Implementation prepared on an isolated branch. Not merged, not deployed and not written to USB.

## Approved continuation

This work block implements the next step after WB-HIVE-BOOT-0009:

- Guardian state machine,
- bounded L0/L1 repair,
- no GRUB/Recovery changes,
- no partition changes,
- no image build,
- no USB write,
- no merge.

## Baseline

~~~
parent branch: wb-hive-boot-0009-health-contract
parent commit: 10e085e2035ec3f1828bf897b9fc1b8c38c1f7db
branch: wb-hive-boot-0010-guardian-l01
architecture input: ADR-0027 (Proposed)
~~~

## Decision

CyberHIVE gains one local Guardian evaluator. systemd remains the process supervisor.

The Guardian evaluates the deterministic WB-0009 health classes and performs at most one allowlisted repair per invocation.

It runs from a systemd timer once per minute.

## Retry and circuit-breaker contract

Per action:

~~~
maximum attempts: 3
window: 600 seconds
minimum attempt spacing: 60 seconds
circuit-open interval after exhaustion: 900 seconds
~~~

Attempt state is persisted before executing the repair action.

Therefore a crash or power loss after action selection still consumes the attempt and cannot bypass the retry budget.

Malformed Guardian state is fail-closed:

- no repair is executed,
- state is not overwritten,
- evidence reports guardian-state-invalid.

## L0 actions

### restart-web

Preconditions:

- current host-disk guard passes,
- management firewall service is active.

Action:

~~~
systemctl restart cyberhive-web.service
~~~

### restart-ssh

Preconditions:

- host-disk guard passes,
- management firewall service is active,
- sshd -t passes.

Action:

~~~
systemctl restart ssh.service
~~~

Guardian never changes SSH authentication configuration to make restart succeed.

### restart-mdns

Preconditions:

- host-disk guard passes,
- management firewall service is active.

Action:

~~~
systemctl restart avahi-daemon.service
~~~

### restart-tailscaled

Used at L0 when tailscaled itself is inactive.

Preconditions:

- host-disk guard passes,
- management firewall service is active.

Action:

~~~
systemctl restart tailscaled.service
~~~

It does not run tailscale up, create a new identity or change auth policy.

## L1 actions

### reconnect-network

Selected when CONNECTED fails with no-local-network.

Preconditions:

- host-disk guard passes,
- management firewall service is active.

Actions are bounded to NetworkManager control:

- start/restart NetworkManager only when inactive,
- reload known connections,
- enable NetworkManager networking,
- enable Wi-Fi radio,
- ask NetworkManager to reconnect existing Ethernet/Wi-Fi devices using existing profiles.

Guardian does not prompt for or synthesize credentials.

### restart-tailscaled for remote subsystem degradation

If CONNECTED passes but Tailscale backend/IP readiness fails while the service exists, Guardian may perform the same bounded tailscaled restart as an L1 remote-subsystem repair.

No re-enrollment is attempted.

## Manual-required conditions

Guardian does not automatically repair:

- host-disk-guard failure,
- persistence unavailable,
- onboarding inactive,
- management firewall inactive,
- invalid sshd configuration,
- malformed Guardian state,
- unknown health reasons/actions.

These conditions remain fail-closed for an operator or a later higher-level recovery work block.

## Persistent state

Guardian state is stored only on the validated CyberHIVE STATE mount:

~~~
/var/lib/cyberhive-persist/state/guardian/state.json
~~~

Mode:

~~~
0600
~~~

The state contains retry/circuit metadata only. No Wi-Fi secrets, Tailscale private state, SSH keys or pairing codes are written there.

Runtime evidence:

~~~
/run/cyberhive/evidence/guardian.json
~~~

Mode:

~~~
0640
~~~

Evidence includes only:

- timestamp,
- LOCAL_SAFE / CONNECTED / REMOTE_READY values,
- selected action/level/reason,
- execution status/reason.

## Scheduling

~~~
OnBootSec=1min
OnUnitActiveSec=1min
RandomizedDelaySec=5s
Persistent=false
~~~

Only one Guardian instance may execute at a time through a runtime flock.

The Guardian service deliberately does not `Wants=` NetworkManager or tailscaled. Timer activation must not implicitly start failed subsystems outside the persisted retry/circuit budget; all such starts/restarts flow through the Guardian action executor.

## Security invariants

Every repair rechecks the host-disk guard at execution time.

Every allowlisted repair also requires the management firewall service to be active.

Guardian does not:

- call reboot or poweroff,
- call grub-editenv,
- mutate EFI,
- mutate A/B slots,
- format filesystems,
- repartition media,
- open LAN SSH,
- disable the management firewall,
- change pairing policy,
- create a new Tailscale identity.

## TDD evidence

RED was observed before implementation for:

1. missing Guardian planner/executor,
2. missing systemd/persistence wiring,
3. firewall fail-closed requirement for all repair actions,
4. missing persistent run-cycle,
5. malformed Guardian-state fail-closed behavior,
6. missing CI/validator gate.

The implementation is accepted for this branch only after all RED cases turn GREEN and inherited suites remain green.

## Rollback

Rollback is code-only:

- disable/remove cyberhive-guardian.timer/service,
- remove the Guardian executable,
- leave state/guardian metadata inert,
- revert to WB-0009 behavior.

No partition, bootloader or persistent identity migration is introduced.

## Explicit stop line

~~~
L2 same-slot reboot: NOT IMPLEMENTED
L3 A/B failover: NOT IMPLEMENTED
L4 Recovery: NOT IMPLEMENTED
GRUB mutation: NO
partition change: NO
image build: NO
USB write: NO
deployment: NO
merge: NO
~~~
