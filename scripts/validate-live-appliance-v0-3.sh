#!/bin/sh
set -eu

root='infra/live-usb/debian-live/config/includes.chroot'
required='docs/work-blocks/WB-HIVE-BOOT-0006-unattended-ota-v0-3.md
docs/adr/ADR-0026-cyberhive-unattended-single-usb-ab-ota.md
docs/runbooks/live-appliance-v0-3.md
docs/security/live-appliance-v0-3-safety.md
infra/live-usb/debian-live/build-unattended-disk-image.sh
infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-persist-init
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-firstboot
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-management-firewall
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-update
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-update-check
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-boot-commit
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-persist-init.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/NetworkManager.service.d/10-cyberhive-persist.conf
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/tailscaled.service.d/10-cyberhive-persist.conf
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-management-firewall.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-boot-commit.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-update-check.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-update-check.timer
infra/live-usb/debian-live/config/includes.chroot/etc/profile.d/20-cyberhive-firstboot.sh
infra/live-usb/debian-live/config/includes.chroot/etc/cyberhive/bootstrap/authorized_keys
infra/live-usb/debian-live/config/includes.chroot/etc/cyberhive/ota/allowed_signers
.github/workflows/live-appliance-v0-3.yml'

printf '%s\n' "$required" | while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ -f "$f" ] || { echo "missing v0.3 path: $f" >&2; exit 1; }
done

for f in \
  infra/live-usb/debian-live/build-unattended-disk-image.sh \
  infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot \
  "$root/usr/local/sbin/cyberhive-persist-init" \
  "$root/usr/local/sbin/cyberhive-firstboot" \
  "$root/usr/local/sbin/cyberhive-management-firewall" \
  "$root/usr/local/sbin/cyberhive-update" \
  "$root/usr/local/sbin/cyberhive-update-check" \
  "$root/usr/local/sbin/cyberhive-boot-commit" \
  "$root/usr/local/sbin/cyberhive-onboarding-init"; do
  sh -n "$f"
done

if grep -R -n -E 'BEGIN (OPENSSH|RSA|EC|PRIVATE) KEY' \
  "$root/etc/cyberhive" infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot docs/work-blocks/WB-HIVE-BOOT-0006-unattended-ota-v0-3.md; then
  echo 'private key material must not be committed' >&2
  exit 1
fi

grep -qx 'CYBERHIVE_LIVE_VERSION="0.3.0-dev"' "$root/etc/cyberhive/live/config.env"
grep -qx 'CYBERHIVE_PERSISTENCE_DEFAULT="usb-state"' "$root/etc/cyberhive/live/config.env"
grep -qx 'CYBERHIVE_EFI_LABEL="CYBERHIVE_EFI"' "$root/etc/cyberhive/live/config.env"
grep -qx 'CYBERHIVE_SLOT_A_LABEL="CYBERHIVE_A"' "$root/etc/cyberhive/live/config.env"
grep -qx 'CYBERHIVE_SLOT_B_LABEL="CYBERHIVE_B"' "$root/etc/cyberhive/live/config.env"
grep -qx 'CYBERHIVE_STATE_LABEL="CYBERHIVE_STATE"' "$root/etc/cyberhive/live/config.env"
grep -F 'cyberhive-dev-channel/channel.json' "$root/etc/cyberhive/live/config.env" >/dev/null

grep -F 'refusing non-USB persistence parent' "$root/usr/local/sbin/cyberhive-persist-init" >/dev/null
grep -F 'mount --bind "$persist/state/tailscale" /var/lib/tailscale' "$root/usr/local/sbin/cyberhive-persist-init" >/dev/null
grep -F 'state/network' "$root/usr/local/sbin/cyberhive-firstboot" >/dev/null
grep -F 'tailscale up --hostname=' "$root/usr/local/sbin/cyberhive-firstboot" >/dev/null
grep -F "^wifi:connected$" "$root/usr/local/sbin/cyberhive-firstboot" >/dev/null || grep -F "'^wifi:connected$'" "$root/usr/local/sbin/cyberhive-firstboot" >/dev/null
if grep -F 'echo "$wifi_password"' "$root/usr/local/sbin/cyberhive-firstboot"; then
  echo 'firstboot must not print Wi-Fi passwords' >&2
  exit 1
fi

grep -F -- "-I cyberhive-dev-release" "$root/usr/local/sbin/cyberhive-update" >/dev/null
grep -F -- "-n cyberhive-ota" "$root/usr/local/sbin/cyberhive-update" >/dev/null
grep -F 'bundle SHA-256 mismatch' "$root/usr/local/sbin/cyberhive-update" >/dev/null
grep -F 'refusing OTA replay/downgrade' "$root/usr/local/sbin/cyberhive-update" >/dev/null
grep -F 'OTA bundle entries must all be regular files' "$root/usr/local/sbin/cyberhive-update" >/dev/null
grep -F -- "--proto-redir '=https'" "$root/usr/local/sbin/cyberhive-update" >/dev/null
grep -F 'STATE/EFI/slot parent mismatch' "$root/usr/local/sbin/cyberhive-update" >/dev/null
grep -F 'refusing OTA on non-USB parent' "$root/usr/local/sbin/cyberhive-update" >/dev/null
if grep -n -E '(^|[[:space:]])(dd|mkfs|wipefs|parted|sgdisk)([[:space:]]|$)' "$root/usr/local/sbin/cyberhive-update"; then
  echo 'runtime OTA must not perform raw disk or partition mutation' >&2
  exit 1
fi

grep -F 'pending_slot' infra/live-usb/debian-live/build-unattended-disk-image.sh >/dev/null
grep -F 'previous_slot' infra/live-usb/debian-live/build-unattended-disk-image.sh >/dev/null
grep -F 'tries=0' infra/live-usb/debian-live/build-unattended-disk-image.sh >/dev/null
grep -F 'live-media-path=$live_path' infra/live-usb/debian-live/build-unattended-disk-image.sh >/dev/null
grep -F 'CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL' infra/live-usb/debian-live/build-unattended-disk-image.sh >/dev/null
grep -F '"usb_written": false' infra/live-usb/debian-live/build-unattended-disk-image.sh >/dev/null
if grep -F '/dev/sd' infra/live-usb/debian-live/build-unattended-disk-image.sh; then
  echo 'image builder must not name a physical disk target' >&2
  exit 1
fi

grep -F "'!' -i tailscale0" "$root/usr/local/sbin/cyberhive-management-firewall" >/dev/null
grep -F -- '--dports 22,80' "$root/usr/local/sbin/cyberhive-management-firewall" >/dev/null
grep -F 'PasswordAuthentication no' "$root/usr/local/sbin/cyberhive-onboarding-init" >/dev/null
grep -F 'key-persistent' "$root/usr/local/sbin/cyberhive-onboarding-init" >/dev/null
grep -F 'state/ssh/host_keys' "$root/usr/local/sbin/cyberhive-onboarding-init" >/dev/null
grep -F "ipaddress.ip_network('100.64.0.0/10')" "$root/usr/local/bin/cyberhive-web" >/dev/null
grep -F 'def is_tailnet_peer' "$root/usr/local/bin/cyberhive-web" >/dev/null
grep -F 'Requires=cyberhive-persist-init.service' "$root/etc/systemd/system/cyberhive-onboarding-init.service" >/dev/null
grep -F 'management blocked' "$root/usr/local/bin/cyberhive-welcome" >/dev/null

grep -F 'chmod 0440 /etc/sudoers.d/90-cyberhive-firstboot' infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot >/dev/null

grep -F 'RuntimeWatchdogSec=90s' "$root/etc/systemd/system.conf.d/30-cyberhive-watchdog.conf" >/dev/null
grep -F 'OnUnitActiveSec=30min' "$root/etc/systemd/system/cyberhive-update-check.timer" >/dev/null

echo 'CyberHIVE Live Appliance v0.3 validation passed'
