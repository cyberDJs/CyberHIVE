#!/bin/sh
set -eu

root='infra/live-usb/debian-live/config/includes.chroot'
required_paths='assets/brand/runtime/cyberdjs-cyberhive-boot.svg
docs/work-blocks/WB-HIVE-BOOT-0005-live-appliance-v0-2.md
docs/adr/ADR-0009-live-appliance-local-control-plane.md
docs/runbooks/live-appliance-v0-2.md
docs/security/live-appliance-v0-2-safety.md
docs/evidence/WB-HIVE-BOOT-0004-physical-boot-2026-09-03.md
infra/live-usb/debian-live/config/package-lists/cyberhive-live.list.chroot
infra/live-usb/debian-live/config/hooks/live/001-cyberhive-live-skeleton.hook.chroot
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-onboarding-init
infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-welcome
infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-web
infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-host-disk-guard
infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-support-bundle
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-onboarding-init.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-web.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-host-disk-guard.service
.github/workflows/live-appliance-v0-2.yml'

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  [ -f "$path" ] || { echo "missing Live Appliance v0.2 path: $path" >&2; exit 1; }
done

for script in \
  infra/live-usb/debian-live/config/hooks/live/001-cyberhive-live-skeleton.hook.chroot \
  infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-onboarding-init \
  infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-welcome \
  infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-host-disk-guard \
  infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-support-bundle \
  infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-live-health \
  infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-inventory \
  infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-role-selector \
  infra/live-usb/debian-live/build-real-image.sh \
  infra/live-usb/debian-live/auto/config; do
  sh -n "$script"
done

python3 -c 'import ast,pathlib; ast.parse(pathlib.Path("infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-web").read_text())'

packages='infra/live-usb/debian-live/config/package-lists/cyberhive-live.list.chroot'
for package in openssh-server avahi-daemon qrencode python3 jq util-linux; do
  grep -qx "$package" "$packages"
done

ssh_base="$root/etc/ssh/sshd_config.d/00-cyberhive-base.conf"
grep -qx 'PermitRootLogin no' "$ssh_base"
grep -qx 'PermitEmptyPasswords no' "$ssh_base"
if grep -q 'PermitRootLogin yes' "$ssh_base"; then echo 'root SSH login must not be enabled' >&2; exit 1; fi

bootstrap="$root/usr/local/sbin/cyberhive-onboarding-init"
grep -F 'blkid -L "$CYBERHIVE_CONFIG_LABEL"' "$bootstrap" >/dev/null
grep -F 'mount -o ro,nodev,nosuid,noexec' "$bootstrap" >/dev/null
grep -F 'PasswordAuthentication no' "$bootstrap" >/dev/null
grep -F 'PasswordAuthentication yes' "$bootstrap" >/dev/null
grep -F 'ssh-keygen -A' "$bootstrap" >/dev/null
grep -F 'rm -f /etc/ssh/ssh_host_*' infra/live-usb/debian-live/config/hooks/live/001-cyberhive-live-skeleton.hook.chroot >/dev/null

web="$root/usr/local/bin/cyberhive-web"
grep -F 'hmac.compare_digest' "$web" >/dev/null
grep -F 'TOO_MANY_REQUESTS' "$web" >/dev/null
grep -F 'HttpOnly; SameSite=Strict' "$web" >/dev/null
grep -F "remote_help': 'disabled" "$web" >/dev/null

web_unit="$root/etc/systemd/system/cyberhive-web.service"
grep -qx 'User=cyberhive' "$web_unit"
grep -qx 'NoNewPrivileges=true' "$web_unit"
grep -qx 'CapabilityBoundingSet=CAP_NET_BIND_SERVICE' "$web_unit"

guard="$root/usr/local/bin/cyberhive-host-disk-guard"
if grep -n -E '(^|[[:space:]])(dd|mkfs|wipefs|parted|fdisk)([[:space:]]|$)' "$guard"; then
  echo 'host disk guard must remain detection-only' >&2
  exit 1
fi
grep -F 'RM 2>/dev/null' "$guard" >/dev/null
grep -F '*,rw,*)' "$guard" >/dev/null

support="$root/usr/local/bin/cyberhive-support-bundle"
if grep -n -E 'ssh-password|pairing-code|web-session-token|/etc/shadow' "$support" | grep -v 'intentionally excluded' >/dev/null; then
  echo 'support bundle must not read authentication material' >&2
  exit 1
fi

grep -q 'CYBERDJS' assets/brand/runtime/cyberdjs-cyberhive-boot.svg
grep -q 'CyberHIVE' assets/brand/runtime/cyberdjs-cyberhive-boot.svg
grep -F 'rsvg-convert --width 640 --height 480' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -F 'librsvg2-bin' .github/workflows/live-usb-real-image-build-gate.yml >/dev/null
grep -F 'librsvg2-bin' .github/workflows/live-usb-real-image-build-manual.yml >/dev/null

grep -F 'CYBERHIVE_REMOTE_HELP_DEFAULT="disabled"' "$root/etc/cyberhive/live/config.env" >/dev/null
grep -F 'CYBERHIVE_MCP_DEFAULT="disabled"' "$root/etc/cyberhive/live/config.env" >/dev/null
grep -F 'CYBERHIVE_DEVBRIDGE_DEFAULT="disabled"' "$root/etc/cyberhive/live/config.env" >/dev/null
grep -x 'Proposed' docs/adr/ADR-0009-live-appliance-local-control-plane.md >/dev/null
grep -F 'merge: NOT AUTHORIZED' docs/notes/WB-HIVE-BOOT-0005-source-map.md >/dev/null

echo 'CyberHIVE Live Appliance v0.2 validation passed'
