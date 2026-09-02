#!/bin/sh
set -eu

required_paths='docs/work-blocks/WB-HIVE-BOOT-0002-build-dry-run.md
docs/runbooks/live-usb-build-dry-run.md
docs/security/live-usb-build-dry-run-safety.md
docs/adr/ADR-0006-live-usb-build-dry-run-boundary.md
infra/live-usb/debian-live/BUILD.md
infra/live-usb/debian-live/build-dry-run.sh
infra/live-usb/debian-live/expected-manifest.md
.github/workflows/live-usb-build-dry-run.yml
scripts/validate-live-usb-build-dry-run.sh'

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  if [ ! -f "$path" ]; then
    echo "missing required live USB build dry-run path: $path" >&2
    exit 1
  fi
done

scan_result="${TMPDIR:-/tmp}/cyberhive-live-build-dry-run-secret-scan.txt"
: > "$scan_result"
secret_pattern='BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|password[[:space:]]*=|token[[:space:]]*=|[s]ecret[[:space:]]*='

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  grep -n -E "$secret_pattern" "$path" >>"$scan_result" 2>/dev/null || true
done

if [ -s "$scan_result" ]; then
  cat "$scan_result" >&2
  echo 'potential credential material found in live USB build dry-run scope' >&2
  exit 1
fi

sh -n infra/live-usb/debian-live/build-dry-run.sh
sh -n scripts/validate-live-usb-build-dry-run.sh

# The dry-run wrapper must not perform real image build, media write,
# host-device mutation, network fetch, or remote access.
blocked_script_result="${TMPDIR:-/tmp}/cyberhive-live-build-dry-run-blocked-script-scan.txt"
: > "$blocked_script_result"
if grep -n -E '(^|[[:space:];|&])(sudo|doas|su|dd|mkfs|mount|umount|ssh|scp|rsync|curl|wget)([[:space:];|&]|$)' \
  infra/live-usb/debian-live/build-dry-run.sh >>"$blocked_script_result" 2>/dev/null; then
  cat "$blocked_script_result" >&2
  echo 'blocked command found in build dry-run wrapper' >&2
  exit 1
fi

if grep -n -E '(^|[[:space:];|&])lb[[:space:]]+build([[:space:];|&]|$)' \
  infra/live-usb/debian-live/build-dry-run.sh >>"$blocked_script_result" 2>/dev/null; then
  cat "$blocked_script_result" >&2
  echo 'actual live image build command must not appear in dry-run wrapper' >&2
  exit 1
fi

grep -R -n '"build_executed": false' infra/live-usb/debian-live/expected-manifest.md infra/live-usb/debian-live/build-dry-run.sh docs/security/live-usb-build-dry-run-safety.md >/dev/null
grep -R -n '"iso_created": false' infra/live-usb/debian-live/expected-manifest.md infra/live-usb/debian-live/build-dry-run.sh docs/security/live-usb-build-dry-run-safety.md >/dev/null
grep -R -n '"usb_written": false' infra/live-usb/debian-live/expected-manifest.md infra/live-usb/debian-live/build-dry-run.sh docs/security/live-usb-build-dry-run-safety.md >/dev/null
grep -R -n '"runtime_verified": false' infra/live-usb/debian-live/expected-manifest.md infra/live-usb/debian-live/build-dry-run.sh docs/security/live-usb-build-dry-run-safety.md >/dev/null

echo 'CyberHIVE live USB build dry-run validation passed'
