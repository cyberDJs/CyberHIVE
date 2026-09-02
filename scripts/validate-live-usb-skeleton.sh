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
infra/live-usb/debian-live/config/hooks/live/001-cyberhive-live-skeleton.hook.chroot
docs/runbooks/live-usb-bootstrap.md
docs/architecture/live-usb-runtime-surface.md
docs/security/live-usb-threat-model.md
docs/ux/cyberhive-runtime-branding.md
assets/brand/runtime/README.md'

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  if [ ! -f "$path" ]; then
    echo "missing required live USB skeleton path: $path" >&2
    exit 1
  fi
done

# Crude but intentional guardrail: the skeleton must not include obvious
# credential material or private-key blocks.
if grep -R -n -E 'BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|password=|token=|secret=' \
  infra/live-usb docs/runbooks/live-usb-bootstrap.md docs/security/live-usb-threat-model.md docs/ux/cyberhive-runtime-branding.md assets/brand/runtime \
  >/tmp/cyberhive-live-secret-scan.txt 2>/dev/null; then
  cat /tmp/cyberhive-live-secret-scan.txt >&2
  echo 'potential secret material found in live USB skeleton' >&2
  exit 1
fi

# The first skeleton must preserve the hard safety defaults.
grep -R -n 'DevBridge/MCP: disabled' infra/live-usb/debian-live >/dev/null
grep -R -n 'Host disk writes: disabled by default' infra/live-usb/debian-live >/dev/null
grep -R -n 'CYBERHIVE_DEVBRIDGE_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null
grep -R -n 'CYBERHIVE_MCP_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null
grep -R -n 'CYBERHIVE_HOST_DISK_WRITE_DEFAULT="disabled"' infra/live-usb/debian-live >/dev/null

echo 'CyberHIVE live USB skeleton validation passed'
