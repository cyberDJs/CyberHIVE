# WB-HIVE-BOOT-0011 - Management Firewall Attestation

## Status

Implementation prepared on an isolated branch. Not merged, not deployed and not written to USB.

## Baseline

~~~
parent branch: wb-hive-boot-0010-guardian-l01
parent commit: ea11114f854d38453bfb51087de06424e50e035a
branch: wb-hive-boot-0011-firewall-attest
~~~

## Problem

The management firewall service is a systemd oneshot with RemainAfterExit=yes.

A later systemd state of active therefore proves that the firewall apply command once completed successfully. It does not prove that the effective IPv4/IPv6 INPUT chain still enforces the CyberHIVE management boundary.

Another firewall manager, operator command or later rule insertion could place a broader ACCEPT rule above the CyberHIVE rules while the service remains active.

Guardian repair must not restore network or management services under that condition.

## Decision

Add a read-only management-firewall attestor:

~~~
/usr/local/bin/cyberhive-management-firewall-attest
~~~

It reads:

~~~
iptables -w 2 -S INPUT
ip6tables -w 2 -S INPUT
~~~

It performs no mutation.

## Attested contract

The beginning of the IPv4 INPUT chain must semantically match:

1. allow HTTP from 169.254.0.0/16 outside tailscale0,
2. allow HTTP from 192.168.0.0/16 outside tailscale0,
3. allow HTTP from 172.16.0.0/12 outside tailscale0,
4. allow HTTP from 10.0.0.0/8 outside tailscale0,
5. allow HTTP from 127.0.0.0/8 outside tailscale0,
6. drop non-Tailscale HTTP,
7. drop non-Tailscale SSH.

The beginning of the IPv6 INPUT chain must semantically match:

1. allow HTTP from fe80::/10 outside tailscale0,
2. allow HTTP from fc00::/7 outside tailscale0,
3. allow HTTP from ::1/128 outside tailscale0,
4. drop non-Tailscale HTTP,
5. drop non-Tailscale SSH.

The attestor parses semantic fields rather than depending on cosmetic iptables rendering such as the presence of -m tcp.

An explicit all-source CIDR is normalized:

- 0.0.0.0/0,
- ::/0.

## Why exact prefix, not rule existence

Checking only iptables -C for individual rules is insufficient.

For example:

~~~
-A INPUT -j ACCEPT
-A INPUT ! -i tailscale0 ... --dport 22 -j DROP
~~~

contains the CyberHIVE DROP rule but the earlier broad ACCEPT bypasses it.

WB-HIVE-BOOT-0011 therefore requires the effective CyberHIVE management rules to occupy the chain prefix in their governed order.

Unexpected rules after that prefix are not rejected by this work block.

## Attestation result

Schema:

~~~
cyberhive.management.firewall.attestation.v1
~~~

PASS requires both IPv4 and IPv6 prefixes to match.

Failure reasons are bounded and non-secret, including:

- ipv4-prefix-mismatch,
- ipv6-prefix-mismatch,
- iptables-unavailable,
- ip6tables-unavailable,
- iptables-query-failed,
- ip6tables-query-failed.

The executable exits:

- 0 on PASS,
- 1 on policy mismatch,
- 2 when the rules cannot be read reliably.

## LOCAL_SAFE integration

cyberhive-live-health executes the attestor read-only.

When live-health already runs as root it calls the attestor directly. For the normal `cyberhive` operator account it uses a narrowly scoped non-interactive sudo capability that permits only `/usr/local/bin/cyberhive-management-firewall-attest`. The attestor uses a fixed `/usr/bin/python3` interpreter, rejects all command-line arguments and does not expose raw `iptables`/`ip6tables` sudo access.

It reports:

~~~
management_firewall=pass|fail
~~~

The deterministic health classifier adds management firewall attestation to LOCAL_SAFE.

Therefore:

- firewall attestation PASS is required for LOCAL_SAFE,
- firewall attestation failure prevents OTA candidate acceptance,
- Tailscale/internet remain independent of LOCAL_SAFE exactly as defined by WB-HIVE-BOOT-0009.

Top-level health schema remains cyberhive.live.health.v1.

## Guardian integration

Before every L0/L1 action Guardian now requires all of:

1. cyberhive-host-disk-guard PASS,
2. cyberhive-management-firewall.service active,
3. cyberhive-management-firewall-attest PASS.

If attestation fails, Guardian returns:

~~~
management-firewall-unattested
~~~

and executes no repair action.

Guardian does not repair firewall drift in this work block.

This is deliberate fail-closed behavior.

## Non-goals

WB-HIVE-BOOT-0011 does not:

- rewrite or reorder firewall rules,
- restart the firewall service automatically,
- manage nftables/firewalld/ufw,
- reboot,
- change GRUB,
- change A/B slots,
- add Recovery,
- repartition media,
- build an image,
- write USB,
- deploy,
- merge.

## TDD evidence

RED was observed before implementation for:

1. missing firewall attestor,
2. missing live-health/classifier integration,
3. missing Guardian attestation precondition,
4. missing CI/validator gate.

The bypass case with a broad ACCEPT rule above the CyberHIVE prefix is an explicit regression test.

## Rollback

Code rollback is a normal revert to WB-HIVE-BOOT-0010.

No persistent schema, identity, GPT, GRUB or firewall-rule migration is introduced.

## ADR

No new ADR is required.

This work block implements and strengthens the existing ADR-0027 fail-closed management/security boundary without changing its architecture.

## Stop line

~~~
firewall auto-repair: NOT IMPLEMENTED
firewall rule mutation change: NO
Guardian L2/L3/L4: NOT IMPLEMENTED
GRUB mutation: NO
partition change: NO
image build: NO
USB write: NO
deployment: NO
merge: NO
~~~
