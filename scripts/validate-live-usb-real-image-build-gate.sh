#!/bin/sh
set -eu

required_paths='.gitignore
.github/workflows/live-usb-real-image-build-gate.yml
.github/workflows/live-usb-real-image-build-manual.yml
docs/work-blocks/WB-HIVE-BOOT-0004-real-image-build-gate.md
docs/runbooks/live-usb-real-image-build-gate.md
docs/security/live-usb-real-image-build-safety.md
docs/adr/ADR-0008-live-usb-real-image-build-gate.md
docs/notes/WB-HIVE-BOOT-0004-source-map.md
infra/live-usb/build-plan.md
infra/live-usb/debian-live/REAL-BUILD-PLAN.md
infra/live-usb/debian-live/REAL-IMAGE-BUILD-GATE.md
infra/live-usb/debian-live/build-real-image.sh
infra/live-usb/debian-live/real-build-manifest.md
scripts/validate-live-usb-real-image-build-gate.sh'

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  if [ ! -f "$path" ]; then
    echo "missing required live USB real image build gate path: $path" >&2
    exit 1
  fi
done

scan_result="${TMPDIR:-/tmp}/cyberhive-live-real-image-build-gate-secret-scan.txt"
: > "$scan_result"
secret_pattern='BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|password[[:space:]]*=|token[[:space:]]*=|[s]ecret[[:space:]]*='

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  grep -n -E "$secret_pattern" "$path" >>"$scan_result" 2>/dev/null || true
done

if [ -s "$scan_result" ]; then
  cat "$scan_result" >&2
  echo 'potential credential material found in live USB real image build gate scope' >&2
  exit 1
fi

sh -n scripts/validate-live-usb-real-image-build-gate.sh
sh -n infra/live-usb/debian-live/build-real-image.sh

grep -R -n 'ISO build: NOT RUN BY PR' docs infra scripts >/dev/null
grep -R -n 'USB write: NOT AUTHORIZED' docs infra scripts >/dev/null
grep -R -n 'hardware boot: NOT CLAIMED' docs infra scripts >/dev/null
grep -R -n 'runtime verification: NOT CLAIMED' docs infra scripts >/dev/null
grep -R -n 'deployment: NOT PERFORMED' docs infra scripts >/dev/null
grep -R -n 'ADR accepted: NO' docs infra scripts >/dev/null

grep -n '^\.cyberhive-live-real-build/$' .gitignore >/dev/null
grep -n '^infra/live-usb/debian-live/live-image-.*\.iso$' .gitignore >/dev/null

grep -n 'CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n 'BUILD_IMAGE_ONLY_NO_USB' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n 'refusing real image build' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n 'refusing real image build: no SHA-256 tool available' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n 'invalid builder label' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n 'out_dir="$repo_root/.cyberhive-live-real-build"' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n '"output_directory": ".cyberhive-live-real-build/"' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n '"usb_written": false' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n '"hardware_booted": false' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n '"runtime_verified": false' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n '"deployment_performed": false' infra/live-usb/debian-live/build-real-image.sh >/dev/null
grep -n '"adr_accepted": false' infra/live-usb/debian-live/build-real-image.sh >/dev/null

if grep -R -n 'CYBERHIVE_LIVE_REAL_BUILD_DIR' \
  infra/live-usb/debian-live/build-real-image.sh \
  docs/runbooks/live-usb-real-image-build-gate.md \
  docs/security/live-usb-real-image-build-safety.md \
  docs/work-blocks/WB-HIVE-BOOT-0004-real-image-build-gate.md; then
  echo 'real image build output directory override must not be present in gate scope' >&2
  exit 1
fi

for path in infra/live-usb/debian-live/build-real-image.sh .github/workflows/live-usb-real-image-build-manual.yml; do
  if grep -n -E '(^|[[:space:]])(dd|mkfs|wipefs|parted)([[:space:]]|$)' "$path"; then
    echo "disk mutation command must not appear in $path" >&2
    exit 1
  fi
  if grep -n -E '(^|[[:space:]])sudo([[:space:]]|$)' "$path"; then
    echo "privileged package or disk mutation command must not appear in $path" >&2
    exit 1
  fi
done

output_existed='false'
if [ -e .cyberhive-live-real-build ]; then
  output_existed='true'
fi

no_token_stdout="${TMPDIR:-/tmp}/cyberhive-real-image-no-token.out"
no_token_stderr="${TMPDIR:-/tmp}/cyberhive-real-image-no-token.err"
no_token_status=0
CYBERHIVE_REAL_IMAGE_BUILDER_LABEL='validator-no-token' \
  sh infra/live-usb/debian-live/build-real-image.sh \
  >"$no_token_stdout" 2>"$no_token_stderr" || no_token_status=$?
if [ "$no_token_status" -ne 2 ]; then
  cat "$no_token_stderr" >&2 || true
  echo "real image build wrapper must refuse missing approval token with exit 2, got $no_token_status" >&2
  exit 1
fi
if [ "$output_existed" = 'false' ] && [ -e .cyberhive-live-real-build ]; then
  echo 'real image build wrapper created output without approval token' >&2
  exit 1
fi

bad_label_stdout="${TMPDIR:-/tmp}/cyberhive-real-image-bad-label.out"
bad_label_stderr="${TMPDIR:-/tmp}/cyberhive-real-image-bad-label.err"
bad_label_status=0
CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB \
CYBERHIVE_REAL_IMAGE_BUILDER_LABEL='bad label with spaces' \
  sh infra/live-usb/debian-live/build-real-image.sh \
  >"$bad_label_stdout" 2>"$bad_label_stderr" || bad_label_status=$?
if [ "$bad_label_status" -ne 2 ]; then
  cat "$bad_label_stderr" >&2 || true
  echo "real image build wrapper must refuse unsafe builder labels with exit 2, got $bad_label_status" >&2
  exit 1
fi
if [ "$output_existed" = 'false' ] && [ -e .cyberhive-live-real-build ]; then
  echo 'real image build wrapper created output for invalid builder label' >&2
  exit 1
fi

grep -n '^on:$' .github/workflows/live-usb-real-image-build-manual.yml >/dev/null
grep -n '^  workflow_dispatch:$' .github/workflows/live-usb-real-image-build-manual.yml >/dev/null
if grep -n '^  pull_request:' .github/workflows/live-usb-real-image-build-manual.yml; then
  echo 'manual real image build workflow must not run on pull_request' >&2
  exit 1
fi
if grep -n '^  push:' .github/workflows/live-usb-real-image-build-manual.yml; then
  echo 'manual real image build workflow must not run on push' >&2
  exit 1
fi

grep -n '^Proposed$' docs/adr/ADR-0008-live-usb-real-image-build-gate.md >/dev/null
grep -n 'File existence is not acceptance' docs/adr/ADR-0008-live-usb-real-image-build-gate.md >/dev/null
grep -n 'ISO build: NOT RUN BY PR' docs/work-blocks/WB-HIVE-BOOT-0004-real-image-build-gate.md >/dev/null

echo 'CyberHIVE live USB real image build gate validation passed'
