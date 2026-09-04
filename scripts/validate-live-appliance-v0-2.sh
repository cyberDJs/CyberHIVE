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

auto_config='infra/live-usb/debian-live/auto/config'
grep -F 'lb config noauto \' "$auto_config" >/dev/null
if grep -n -E '^[[:space:]]*lb[[:space:]]+config[[:space:]]*\\[[:space:]]*$' "$auto_config"; then
  echo 'auto/config must call lb config with noauto to prevent recursive re-entry' >&2
  exit 1
fi

python3 -c 'import ast,pathlib; ast.parse(pathlib.Path("infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-web").read_text())'

packages='infra/live-usb/debian-live/config/package-lists/cyberhive-live.list.chroot'
for package in openssh-server avahi-daemon qrencode python3 jq util-linux; do
  grep -qx "$package" "$packages"
done

ssh_base="$root/etc/ssh/sshd_config.d/00-cyberhive-base.conf"
grep -qx 'PermitRootLogin no' "$ssh_base"
grep -qx 'PermitEmptyPasswords no' "$ssh_base"
if grep -q 'PermitRootLogin yes' "$ssh_base"; then echo 'root SSH login must not be enabled' >&2; exit 1; fi

hook='infra/live-usb/debian-live/config/hooks/live/001-cyberhive-live-skeleton.hook.chroot'
grep -F 'groupadd --system cyberhive-control' "$hook" >/dev/null
grep -F 'useradd --system --gid cyberhive-control' "$hook" >/dev/null
grep -F 'rm -f /etc/ssh/ssh_host_*' "$hook" >/dev/null

bootstrap="$root/usr/local/sbin/cyberhive-onboarding-init"
grep -F 'blkid -L "$CYBERHIVE_CONFIG_LABEL"' "$bootstrap" >/dev/null
grep -F 'mount -o ro,nodev,nosuid,noexec' "$bootstrap" >/dev/null
grep -F 'PasswordAuthentication no' "$bootstrap" >/dev/null
grep -F 'PasswordAuthentication yes' "$bootstrap" >/dev/null
grep -F 'install -d -m 0755 -o root -g root /run/sshd' "$bootstrap" >/dev/null
grep -F 'ssh-keygen -A' "$bootstrap" >/dev/null
grep -F 'ssh-bootstrap-status' "$bootstrap" >/dev/null
grep -F 'chown root:cyberhive "$CYBERHIVE_PRIVATE_DIR"' "$bootstrap" >/dev/null
grep -F 'chmod 0750 "$CYBERHIVE_PRIVATE_DIR"' "$bootstrap" >/dev/null
grep -F '"$CYBERHIVE_CONTROL_DIR/pairing-code"' "$bootstrap" >/dev/null
if grep -F '"$CYBERHIVE_PRIVATE_DIR/pairing-code"' "$bootstrap"; then
  echo 'pairing code must not share SSH private runtime directory' >&2
  exit 1
fi

web="$root/usr/local/bin/cyberhive-web"
grep -F "PAIR_FILE = CONTROL / 'pairing-code'" "$web" >/dev/null
grep -F "mode_file = STATE / 'ssh-mode'" "$web" >/dev/null
grep -F 'hmac.compare_digest' "$web" >/dev/null
grep -F 'TOO_MANY_REQUESTS' "$web" >/dev/null
grep -F 'HttpOnly; SameSite=Strict' "$web" >/dev/null
grep -F "remote_help': 'disabled" "$web" >/dev/null
if grep -F '/run/cyberhive/private' "$web"; then
  echo 'LAN-facing web process must not read CyberHIVE SSH private runtime state' >&2
  exit 1
fi

web_unit="$root/etc/systemd/system/cyberhive-web.service"
grep -qx 'User=cyberhive-web' "$web_unit"
grep -qx 'Group=cyberhive-control' "$web_unit"
grep -F 'Wants=cyberhive-onboarding-init.service network-online.target' "$web_unit" >/dev/null
if grep -F 'Requires=cyberhive-onboarding-init.service' "$web_unit"; then
  echo 'browser control plane must not share the SSH bootstrap failure domain' >&2
  exit 1
fi
grep -qx 'NoNewPrivileges=true' "$web_unit"
grep -qx 'ProtectHome=true' "$web_unit"
grep -qx 'CapabilityBoundingSet=CAP_NET_BIND_SERVICE' "$web_unit"
if grep -qx 'User=cyberhive' "$web_unit"; then
  echo 'browser control plane must not run as SSH/login user' >&2
  exit 1
fi

health="$root/usr/local/bin/cyberhive-live-health"
grep -F "status='degraded'" "$health" >/dev/null
grep -F 'service_state cyberhive-onboarding-init' "$health" >/dev/null
grep -F 'ssh-bootstrap-status' "$health" >/dev/null

guard="$root/usr/local/bin/cyberhive-host-disk-guard"
if grep -n -E '(^|[[:space:]])(dd|mkfs|wipefs|parted|fdisk)([[:space:]]|$)' "$guard"; then
  echo 'host disk guard must remain detection-only' >&2
  exit 1
fi
if grep -F 'allowed_parent' "$guard" >/dev/null; then
  grep -F 'TRAN "$candidate"' "$guard" >/dev/null
  grep -F 'fully validated CyberHIVE USB parent' "$guard" >/dev/null
else
  grep -F 'RM 2>/dev/null' "$guard" >/dev/null
fi
grep -F '*,rw,*)' "$guard" >/dev/null

support="$root/usr/local/bin/cyberhive-support-bundle"
if grep -n -E '^[[:space:]]*(cat|cp|tar|sed|awk|grep)[[:space:]].*(ssh-password|pairing-code|web-session-token|/etc/shadow)' "$support"; then
  echo 'support bundle must not read authentication material' >&2
  exit 1
fi

grep -q 'CYBERDJS' assets/brand/runtime/cyberdjs-cyberhive-boot.svg
grep -q 'CyberHIVE' assets/brand/runtime/cyberdjs-cyberhive-boot.svg
build_real='infra/live-usb/debian-live/build-real-image.sh'
grep -F 'rsvg-convert --width 640 --height 480' "$build_real" >/dev/null
grep -F 'for bootloader in isolinux syslinux_common grub-pc; do' "$build_real" >/dev/null
grep -F 'binary/boot/grub/splash.png' "$build_real" >/dev/null
if grep -F 'for bootloader in isolinux grub-efi; do' "$build_real"; then
  echo 'UEFI branding must use live-build shared grub-pc source, not a nonexistent grub-efi theme path' >&2
  exit 1
fi
for workflow in .github/workflows/live-usb-real-image-build-gate.yml .github/workflows/live-usb-real-image-build-manual.yml; do
  grep -F 'librsvg2-bin' "$workflow" >/dev/null
  grep -F 'fonts-dejavu-core' "$workflow" >/dev/null
done

grep -F 'CYBERHIVE_WEB_USER="cyberhive-web"' "$root/etc/cyberhive/live/config.env" >/dev/null
grep -F 'CYBERHIVE_CONTROL_GROUP="cyberhive-control"' "$root/etc/cyberhive/live/config.env" >/dev/null
grep -F 'CYBERHIVE_REMOTE_HELP_DEFAULT="disabled"' "$root/etc/cyberhive/live/config.env" >/dev/null
grep -F 'CYBERHIVE_MCP_DEFAULT="disabled"' "$root/etc/cyberhive/live/config.env" >/dev/null
grep -F 'CYBERHIVE_DEVBRIDGE_DEFAULT="disabled"' "$root/etc/cyberhive/live/config.env" >/dev/null
grep -x 'Proposed' docs/adr/ADR-0009-live-appliance-local-control-plane.md >/dev/null
grep -F 'merge: NOT AUTHORIZED' docs/notes/WB-HIVE-BOOT-0005-source-map.md >/dev/null

echo 'CyberHIVE Live Appliance v0.2 validation passed'
