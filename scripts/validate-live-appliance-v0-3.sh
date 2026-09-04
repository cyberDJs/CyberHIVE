#!/bin/sh
set -eu

root='infra/live-usb/debian-live/config/includes.chroot'
required='docs/work-blocks/WB-HIVE-BOOT-0006-unattended-ota-v0-3.md
docs/adr/ADR-0026-cyberhive-unattended-single-usb-ab-ota.md
docs/runbooks/live-appliance-v0-3.md
docs/security/live-appliance-v0-3-safety.md
infra/live-usb/debian-live/build-unattended-disk-image.sh
infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot
infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-host-disk-guard
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
  "$root/usr/local/bin/cyberhive-host-disk-guard" \
  "$root/usr/local/sbin/cyberhive-persist-init" \
  "$root/usr/local/sbin/cyberhive-firstboot" \
  "$root/usr/local/sbin/cyberhive-management-firewall" \
  "$root/usr/local/sbin/cyberhive-update" \
  "$root/usr/local/sbin/cyberhive-update-check" \
  "$root/usr/local/sbin/cyberhive-boot-commit" \
  "$root/usr/local/sbin/cyberhive-onboarding-init"; do
  sh -n "$f"
done

line_of() {
  file=$1
  text=$2
  grep -nF "$text" "$file" | head -n 1 | cut -d: -f1
}

assert_before() {
  file=$1
  first=$2
  second=$3
  first_line=$(line_of "$file" "$first")
  second_line=$(line_of "$file" "$second")
  [ -n "$first_line" ] && [ -n "$second_line" ] && [ "$first_line" -lt "$second_line" ] || {
    echo "ordering invariant failed in $file: $first before $second" >&2
    exit 1
  }
}

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

update="$root/usr/local/sbin/cyberhive-update"
grep -F -- "-I cyberhive-dev-release" "$update" >/dev/null
grep -F -- "-n cyberhive-ota" "$update" >/dev/null
grep -F 'bundle SHA-256 mismatch' "$update" >/dev/null
grep -F 'refusing OTA replay/downgrade/quarantine' "$update" >/dev/null
grep -F 'refusing previously failed OTA release' "$update" >/dev/null
grep -F 'OTA bundle entries must all be regular files' "$update" >/dev/null
grep -F -- "--proto-redir '=https'" "$update" >/dev/null
grep -F 'STATE/EFI/A/B parent mismatch' "$update" >/dev/null
grep -F 'refusing OTA on non-USB parent' "$update" >/dev/null
grep -F 'mounted STATE identity mismatch' "$update" >/dev/null
grep -F 'another CyberHIVE OTA operation is active' "$update" >/dev/null
grep -F 'pending-release-id' "$update" >/dev/null
grep -F 'pending-previous-slot' "$update" >/dev/null
grep -F 'pending-phase' "$update" >/dev/null
assert_before "$update" 'atomic_text "$sequence" "$otadir/pending-sequence"' 'grub-editenv "$envfile" set'
assert_before "$update" 'atomic_text "$inactive" "$otadir/pending-slot"' 'grub-editenv "$envfile" set'
if grep -n -E '(^|[[:space:]])(dd|mkfs|wipefs|parted|sgdisk)([[:space:]]|$)' "$update"; then
  echo 'runtime OTA must not perform raw disk or partition mutation' >&2
  exit 1
fi

commit="$root/usr/local/sbin/cyberhive-boot-commit"
grep -F 'candidate persistence unavailable; rebooting for automatic rollback' "$commit" >/dev/null
grep -F 'EFI/current-slot parent mismatch' "$commit" >/dev/null
grep -F 'refusing non-USB EFI/current-slot parent' "$commit" >/dev/null
grep -F 'mounted STATE identity/parent mismatch' "$commit" >/dev/null
grep -F 'mount -o ro,nodev,nosuid,noexec "$efi_dev" "$efi_mount"' "$commit" >/dev/null
grep -F 'commit-transaction.json' "$commit" >/dev/null
grep -F 'invalid commit transaction schema' "$commit" >/dev/null
grep -F 'invalid transaction new sequence' "$commit" >/dev/null
grep -F 'incomplete-commit-rollback' "$commit" >/dev/null
grep -F 'rollback-detected' "$commit" >/dev/null
grep -F 'quarantine_release "$state_pending_release" "$state_pending_sequence" health-gate' "$commit" >/dev/null
grep -F 'Anti-downgrade state is durable before pending boot state is cleared in EFI.' "$commit" >/dev/null
grep -F 'atomic_text "$state_pending_sequence" "$otadir/current-sequence"' "$commit" >/dev/null

host_guard="$root/usr/local/bin/cyberhive-host-disk-guard"
grep -F 'allowed_parent' "$host_guard" >/dev/null
grep -F 'TRAN "$candidate"' "$host_guard" >/dev/null
if grep -F 'NAME,TYPE,RM' "$host_guard"; then
  echo 'host-disk guard must not classify the CyberHIVE device by RM alone' >&2
  exit 1
fi
grep -F 'fully validated CyberHIVE USB parent' "$host_guard" >/dev/null

builder='infra/live-usb/debian-live/build-unattended-disk-image.sh'
grep -F 'pending_slot' "$builder" >/dev/null
grep -F 'previous_slot' "$builder" >/dev/null
grep -F 'tries=0' "$builder" >/dev/null
grep -F 'live-media-path=$live_path' "$builder" >/dev/null
grep -F 'CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL' "$builder" >/dev/null
grep -F '"usb_written": false' "$builder" >/dev/null
if grep -F '/dev/sd' "$builder"; then
  echo 'image builder must not name a physical disk target' >&2
  exit 1
fi

firewall="$root/usr/local/sbin/cyberhive-management-firewall"
grep -F -- '--dport 22 -j DROP' "$firewall" >/dev/null
grep -F '192.168.0.0/16' "$firewall" >/dev/null
grep -F '172.16.0.0/12' "$firewall" >/dev/null
grep -F '10.0.0.0/8' "$firewall" >/dev/null
grep -F -- '--dport 80 -j DROP' "$firewall" >/dev/null
assert_before "$firewall" "--dport 80 -j DROP" 'for net in 127.0.0.0/8'

grep -F 'PasswordAuthentication no' "$root/usr/local/sbin/cyberhive-onboarding-init" >/dev/null
grep -F 'key-persistent' "$root/usr/local/sbin/cyberhive-onboarding-init" >/dev/null
grep -F 'state/ssh/host_keys' "$root/usr/local/sbin/cyberhive-onboarding-init" >/dev/null
grep -F "ipaddress.ip_network('100.64.0.0/10')" "$root/usr/local/bin/cyberhive-web" >/dev/null
grep -F 'def is_tailnet_peer' "$root/usr/local/bin/cyberhive-web" >/dev/null
grep -F 'Requires=cyberhive-persist-init.service' "$root/etc/systemd/system/cyberhive-onboarding-init.service" >/dev/null
grep -F 'SSH blocked; HTTP pairing only' "$root/usr/local/bin/cyberhive-welcome" >/dev/null

grep -F 'chmod 0440 /etc/sudoers.d/90-cyberhive-firstboot' infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot >/dev/null

grep -F 'RuntimeWatchdogSec=90s' "$root/etc/systemd/system.conf.d/30-cyberhive-watchdog.conf" >/dev/null
grep -F 'OnUnitActiveSec=30min' "$root/etc/systemd/system/cyberhive-update-check.timer" >/dev/null

grep -F 'pre-unattended-disk-usage.txt' .github/workflows/live-usb-real-image-build-gate.yml >/dev/null
grep -F 'unattended-console.txt' .github/workflows/live-usb-real-image-build-gate.yml >/dev/null
grep -F 'Upload lightweight build diagnostics' .github/workflows/live-usb-real-image-build-gate.yml >/dev/null

echo 'CyberHIVE Live Appliance v0.3 validation passed'
