#!/bin/sh
set -eu

required_paths='.gitignore
.github/workflows/live-usb-real-build-plan.yml
docs/work-blocks/WB-HIVE-BOOT-0003-real-build-plan.md
docs/runbooks/live-usb-real-build-plan.md
docs/security/live-usb-real-build-safety.md
docs/adr/ADR-0007-live-usb-real-build-gate.md
docs/notes/WB-HIVE-BOOT-0003-source-map.md
infra/live-usb/build-plan.md
infra/live-usb/debian-live/REAL-BUILD-PLAN.md
infra/live-usb/debian-live/real-build-manifest.md
scripts/validate-live-usb-real-build-plan.sh'

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  if [ ! -f "$path" ]; then
    echo "missing required live USB real build plan path: $path" >&2
    exit 1
  fi
done

scan_result="${TMPDIR:-/tmp}/cyberhive-live-real-build-plan-secret-scan.txt"
: > "$scan_result"
secret_pattern='BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|password[[:space:]]*=|token[[:space:]]*=|[s]ecret[[:space:]]*='

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  grep -n -E "$secret_pattern" "$path" >>"$scan_result" 2>/dev/null || true
done

if [ -s "$scan_result" ]; then
  cat "$scan_result" >&2
  echo 'potential credential material found in live USB real build plan scope' >&2
  exit 1
fi

sh -n scripts/validate-live-usb-real-build-plan.sh

grep -R -n 'ISO build: NOT EXECUTED' docs infra scripts >/dev/null
grep -R -n 'USB write: NOT AUTHORIZED' docs infra scripts >/dev/null
grep -R -n 'runtime verification: NOT CLAIMED' docs infra scripts >/dev/null
grep -R -n 'ADR accepted: NO' docs infra scripts >/dev/null

grep -n '^\.cyberhive-live-real-build/$' .gitignore >/dev/null
grep -n '^infra/live-usb/debian-live/live-image-.*\.iso$' .gitignore >/dev/null

grep -R -n '"usb_written": false' docs/runbooks/live-usb-real-build-plan.md infra/live-usb/debian-live/real-build-manifest.md >/dev/null
grep -R -n '"hardware_booted": false' docs/runbooks/live-usb-real-build-plan.md infra/live-usb/debian-live/real-build-manifest.md >/dev/null
grep -R -n '"runtime_verified": false' docs/runbooks/live-usb-real-build-plan.md infra/live-usb/debian-live/real-build-manifest.md >/dev/null

grep -R -n 'Candidate only, not accepted' docs/work-blocks/WB-HIVE-BOOT-0003-real-build-plan.md >/dev/null
grep -R -n '^## Status$' docs/adr/ADR-0007-live-usb-real-build-gate.md >/dev/null
grep -R -n '^Proposed$' docs/adr/ADR-0007-live-usb-real-build-gate.md >/dev/null

echo 'CyberHIVE live USB real build plan validation passed'
