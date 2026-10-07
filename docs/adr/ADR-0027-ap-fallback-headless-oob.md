# ADR-0027 - AP fallback and headless OOB network onboarding

Status: proposed
Date: 2026-10-07

## Context

CyberHIVE must remain recoverable when Ethernet is absent and no saved Wi-Fi connection can be activated. The appliance must still preserve the existing management firewall, SSH policy, OTA/recovery path and local-first behavior.

WB-HIVE-BOOT-0011 is the verified parent stack. No WB-HIVE-BOOT-0012 exists in the repository at the time of this decision.

## Decision

Add a dedicated OOB network service separate from the normal CyberHIVE management web service.

The service will:

1. Prefer any usable Ethernet uplink.
2. Prefer saved Wi-Fi when Ethernet is unavailable.
3. Wait a bounded 45-second window before fallback.
4. Create one deterministic NetworkManager AP profile named `cyberhive-oob` only when no usable uplink exists.
5. Use the dedicated subnet `10.42.0.0/24` with appliance address `10.42.0.1`.
6. Keep provisioning state and per-installation AP credentials only on the CyberHIVE removable STATE partition.
7. Apply a candidate Wi-Fi profile transactionally.
8. Persist the candidate only after NetworkManager reports connected L3 state.
9. Restore the fallback AP after a failed candidate.
10. Remove the AP after a verified uplink becomes active.
11. Re-enter fallback after all usable uplinks remain unavailable for the bounded fallback window.

The OOB service is not the normal management plane. It must not expose role mutation, support-bundle generation, SSH control, OTA control, Tailscale control or Guardian actions.

## Credential delivery

A secure headless appliance needs an out-of-band way for the operator to learn its unique AP credential. The runtime may generate and persist a unique credential, but production acceptance requires that the credential be provisioned or delivered through a trusted physical/packaging workflow.

An open AP or a credential encoded in a publicly visible SSID is rejected because physical proximity is not identity and it would expose submitted upstream Wi-Fi credentials.

Until the trusted credential-delivery path is proven on real hardware, this WB cannot be promoted as fully verified headless onboarding.

## Consequences

Positive:
- no dependency on Internet or cloud control;
- no change to the normal management authentication boundary;
- Ethernet remains first class;
- failed onboarding remains recoverable;
- saved Wi-Fi survives reboot through existing STATE persistence.

Negative:
- an additional root network service is introduced;
- concurrent AP/client behavior depends on Wi-Fi hardware/driver capability;
- real-device validation is mandatory;
- production headless usability depends on the physical credential-delivery workflow.

## Rejected alternatives

- Extend `cyberhive-web` with unrestricted NetworkManager privileges: rejected because it expands the normal management attack surface.
- Open fallback AP: rejected because it exposes provisioning to any nearby station.
- Cloud bootstrap: rejected because CyberHIVE is local-first and must remain useful offline.
- Automatic Internet reachability as the success criterion: rejected because LAN-only operation is valid.

## Verification

Required before merge:
- exact-head CI;
- fallback activates only after the bounded no-uplink window;
- Ethernet suppresses AP fallback;
- saved Wi-Fi suppresses AP fallback;
- unique credential persists over reboot;
- candidate success reaches L3 state before AP shutdown;
- bad credentials restore AP fallback;
- loss of all uplinks restores AP fallback;
- management firewall and SSH invariants remain unchanged;
- OTA/recovery validation remains green;
- real-device test on the target CyberHIVE hardware.

## Migration / rollback

The change is additive. Rollback is disabling/removing `cyberhive-oob-network.service` and its runtime helper. Existing NetworkManager profiles, management firewall, Guardian state and OTA slots remain authoritative.

No production deployment, DNS, public exposure, USB write or merge is authorized by this ADR.
