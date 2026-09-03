# CyberHIVE Live Appliance v0.2 Runbook

## Scope

Operational contract for `WB-HIVE-BOOT-0005`.

This runbook covers repository validation and the future v0.2 appliance acceptance. It does not authorize a media write or merge.

## Expected local console

After boot the operator should see:

```text
CYBERDJS / CyberHIVE
LIVE APPLIANCE

Web:  http://cyberhive.local
IPv4: http://<address>
SSH:  ssh cyberhive@<address>
Auth: key | ephemeral-password
Pair: <boot-session-code>
```

A QR code should encode the preferred browser URL when available.

Temporary SSH password and pairing code are local-console information. They must not be printed to SSH pseudo-terminals or support bundles.

## SSH key mode

Prepare a filesystem labeled:

```text
CYBERHIVE_CFG
```

Place a public-key file at its root:

```text
authorized_keys
```

At boot CyberHIVE mounts the filesystem read-only and imports the public keys for the `cyberhive` user.

Expected state:

```text
SSH auth mode: key
PasswordAuthentication no
PermitRootLogin no
```

## SSH fallback mode

When no valid config key exists, CyberHIVE generates an ephemeral password for the `cyberhive` account.

Expected state:

```text
SSH auth mode: ephemeral-password
PermitRootLogin no
```

The password is valid only for that live boot unless a future persistence policy explicitly says otherwise.

## Browser onboarding

From another machine on the same LAN:

1. open `http://cyberhive.local`
2. if mDNS is unavailable, use the IPv4 URL printed locally
3. enter the pairing code shown on the physical CyberHIVE console
4. inspect health/network/SSH/host-disk state
5. select a boot-session role if needed

Role selection must not silently enable DevBridge, MCP, host-disk writes or remote help.

## Runtime checks

```sh
cyberhive-live-health
cyberhive-inventory
cyberhive-host-disk-guard
cyberhive-support-bundle
systemctl is-active ssh
systemctl is-active cyberhive-web
systemctl is-active avahi-daemon
```

## Physical acceptance checklist

- [ ] branded boot graphic visible
- [ ] local dynamic welcome visible
- [ ] IPv4 detected when DHCP is available
- [ ] `cyberhive.local` resolves from another LAN machine
- [ ] browser page loads
- [ ] control actions reject an unpaired browser
- [ ] correct pairing code succeeds
- [ ] SSH key mode works with `CYBERHIVE_CFG`
- [ ] key mode rejects password authentication
- [ ] fallback password mode works without config key
- [ ] root SSH login is rejected
- [ ] host-disk guard PASS with attached internal disk present
- [ ] support bundle excludes temporary credentials
- [ ] reboot rotates password/pairing session

## Stop lines

Do not claim any of these without separate evidence:

```text
v0.2 physical boot: NOT VERIFIED until rebuilt and booted
host disk writes: NOT AUTHORIZED
DevBridge/MCP: NOT ENABLED
remote help: NOT ENABLED
deployment: NOT PERFORMED
ADR-0009 accepted: NO
```
