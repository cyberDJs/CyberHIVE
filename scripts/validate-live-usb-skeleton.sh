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

# Guardrail: every required skeleton file is scanned for obvious credential
# material or private-key blocks. Keep the pattern conservative and reviewable.
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

# The first skeleton must preserve the hard safety defaults.
grep -R -n 'DevBridge/MCP: disabled' infra/live-usb/debian-live >/dev/null
grep -R -n 'Host disk writes: disabled by default' infra/live-usb/debian-live >/dev/null
grep -R -n 'CYBERHIVE_DEVBRIDGE_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null
grep -R -n 'CYBERHIVE_MCP_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null
grep -R -n 'CYBERHIVE_HOST_DISK_WRITE_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null

# v0.1 must not ship local discovery daemons until discovery policy is explicit.
if grep -R -n '^avahi-daemon$' infra/live-usb/debian-live/config/package-lists >/tmp/cyberhive-live-discovery-daemon-scan.txt 2>/dev/null; then
  cat /tmp/cyberhive-live-discovery-daemon-scan.txt >&2
  echo 'local discovery daemon must not be enabled in v0.1 package seed' >&2
  exit 1
fi

echo 'CyberHIVE live USB skeleton validation passed'
