#!/bin/sh
set -eu

required_paths='infra/live-usb/README.md
infra/live-usb/build-plan.md
infra/live-usb/safety-boundary.md
infra/live-usb/debian-live/README.md
infra/live-usb/debian-live/auto/config
infra/live-usb/debian-live/config/package-lists/cyberhive-live.list.chroot
infra/live-usb/debian-live/config/includes.chroot/etc/cyberhive/live/config.env
infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-live-health
infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-role-selector
infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-inventory
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-live-agent.service
infra/live-usb/debian-live/config/includes.chroot/usr/lib/tmpfiles.d/cyberhive-live.conf
infra/live-usb/debian-live/config/hooks/live/001-cyberhive-live-skeleton.hook.chroot
docs/runbooks/live-usb-bootstrap.md
docs/architecture/live-usb-runtime-surface.md
docs/security/live-usb-threat-model.md
docs/ux/cyberhive-runtime-branding.md
assets/brand/runtime/README.md
.github/workflows/live-usb-skeleton.yml
scripts/validate-live-usb-skeleton.sh'

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  if [ ! -f "$path" ]; then
    echo "missing required live USB skeleton path: $path" >&2
    exit 1
  fi
done

scan_result="${TMPDIR:-/tmp}/cyberhive-live-secret-scan.txt"
: > "$scan_result"
secret_pattern='BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|password[[:space:]]*=|token[[:space:]]*=|[s]ecret[[:space:]]*='
printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  grep -n -E "$secret_pattern" "$path" >>"$scan_result" 2>/dev/null || true
done
if [ -s "$scan_result" ]; then
  cat "$scan_result" >&2
  echo 'potential secret material found in live USB skeleton' >&2
  exit 1
fi

live_config='infra/live-usb/debian-live/config/includes.chroot/etc/cyberhive/live/config.env'
live_version=$(sed -n 's/^CYBERHIVE_LIVE_VERSION="\([^"]*\)"/\1/p' "$live_config")
[ -n "$live_version" ] || { echo 'CYBERHIVE_LIVE_VERSION missing' >&2; exit 1; }

grep -R -n 'CYBERHIVE_DEVBRIDGE_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null
grep -R -n 'CYBERHIVE_MCP_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null
grep -R -n 'CYBERHIVE_HOST_DISK_WRITE_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null

case "$live_version" in
  0.1.*)
    grep -R -n 'DevBridge/MCP: disabled' infra/live-usb/debian-live >/dev/null
    grep -R -n 'Host disk writes: disabled by default' infra/live-usb/debian-live >/dev/null
    if grep -R -n '^avahi-daemon$' infra/live-usb/debian-live/config/package-lists >/tmp/cyberhive-live-discovery-daemon-scan.txt 2>/dev/null; then
      cat /tmp/cyberhive-live-discovery-daemon-scan.txt >&2
      echo 'local discovery daemon must not be enabled in v0.1 package seed' >&2
      exit 1
    fi
    ;;
  0.2.*)
    grep -R -n '^avahi-daemon$' infra/live-usb/debian-live/config/package-lists >/dev/null
    grep -R -n 'CYBERHIVE_REMOTE_HELP_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null
    [ -f docs/security/live-appliance-v0-2-safety.md ]
    [ -f scripts/validate-live-appliance-v0-2.sh ]
    ;;
  0.3.*)
    grep -R -n '^avahi-daemon$' infra/live-usb/debian-live/config/package-lists >/dev/null
    grep -R -n 'CYBERHIVE_REMOTE_HELP_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null
    [ -f docs/security/live-appliance-v0-2-safety.md ]
    [ -f scripts/validate-live-appliance-v0-2.sh ]
    [ -f docs/security/live-appliance-v0-3-safety.md ]
    [ -f scripts/validate-live-appliance-v0-3.sh ]
    grep -F 'CYBERHIVE_PERSISTENCE_DEFAULT="usb-state"' "$live_config" >/dev/null
    grep -F 'CYBERHIVE_STATE_LABEL="CYBERHIVE_STATE"' "$live_config" >/dev/null
    ;;
  *)
    echo "unsupported live skeleton policy version: $live_version" >&2
    exit 1
    ;;
esac

echo "CyberHIVE live USB skeleton validation passed for $live_version"
