#!/bin/sh
set -eu

root='infra/live-usb/debian-live/config/includes.chroot'
network="$root/usr/local/sbin/cyberhive-oob-network"
onboard="$root/usr/local/sbin/cyberhive-oob-onboard"
network_unit="$root/etc/systemd/system/cyberhive-oob-network.service"
onboard_unit="$root/etc/systemd/system/cyberhive-oob-onboard.service"
hook='infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot'

for path in "$network" "$onboard" "$network_unit" "$onboard_unit"   'docs/adr/ADR-0027-ap-fallback-headless-oob.md'   'docs/work-blocks/WB-HIVE-BOOT-0013-ap-fallback-oob.md'; do
  test -f "$path" || { echo "missing OOB artifact: $path" >&2; exit 1; }
done

python3 -c 'import ast,pathlib; ast.parse(pathlib.Path("'"$onboard"'").read_text())'

grep -F 'FALLBACK_SECONDS=45' "$network" >/dev/null
grep -F 'AP_ADDR=10.42.0.1/24' "$network" >/dev/null
grep -F 'wifi-sec.key-mgmt wpa-psk' "$network" >/dev/null
grep -F 'connection.autoconnect no' "$network" >/dev/null
grep -F 'has_uplink()' "$network" >/dev/null
grep -F 'CYBERHIVE_PERSIST_ROOT/state/network/oob-ap.env' "$network" >/dev/null

grep -F 'AP_ADDR = "10.42.0.1"' "$onboard" >/dev/null
grep -F 'AP_PORT = 8080' "$onboard" >/dev/null
grep -F 'def connected_l3' "$onboard" >/dev/null
grep -F 'def persist_profile' "$onboard" >/dev/null
grep -F 'candidate-not-connected' "$onboard" >/dev/null
grep -F 'provisioning-subnet-only' "$onboard" >/dev/null

grep -F 'ProtectSystem=strict' "$network_unit" >/dev/null
grep -F 'ProtectSystem=strict' "$onboard_unit" >/dev/null
grep -F 'ReadWritePaths=/run/cyberhive /var/lib/cyberhive-persist/state/network /etc/NetworkManager/system-connections' "$network_unit" >/dev/null
grep -F 'ReadWritePaths=/run/cyberhive /var/lib/cyberhive-persist/state/network /etc/NetworkManager/system-connections' "$onboard_unit" >/dev/null

grep -F 'chmod 0755 /usr/local/sbin/cyberhive-oob-network' "$hook" >/dev/null
grep -F 'chmod 0755 /usr/local/sbin/cyberhive-oob-onboard' "$hook" >/dev/null
grep -F 'systemctl enable cyberhive-oob-network.service' "$hook" >/dev/null
grep -F 'systemctl enable cyberhive-oob-onboard.service' "$hook" >/dev/null

# Existing management and SSH boundaries must remain present.
grep -F -- '--dport 22 -j DROP' "$root/usr/local/sbin/cyberhive-management-firewall" >/dev/null
grep -F -- '--dport 80 -j DROP' "$root/usr/local/sbin/cyberhive-management-firewall" >/dev/null
grep -F 'PasswordAuthentication no' "$root/usr/local/sbin/cyberhive-onboarding-init" >/dev/null

python3 scripts/test-cyberhive-oob-onboarding.py
python3 scripts/test-cyberhive-oob-provisioner.py

echo 'CyberHIVE headless OOB onboarding validation passed'
