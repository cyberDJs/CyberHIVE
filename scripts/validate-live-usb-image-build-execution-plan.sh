#!/bin/sh
set -eu

required_paths='.github/workflows/live-usb-image-build-execution-plan.yml
docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md
docs/runbooks/live-usb-image-build-execution-plan.md
docs/security/live-usb-image-build-execution-safety.md
docs/notes/WB-HIVE-BOOT-0005-source-map.md
infra/live-usb/build-plan.md
infra/live-usb/debian-live/IMAGE-BUILD-EXECUTION-PLAN.md
scripts/validate-live-usb-image-build-execution-plan.sh'

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  if [ ! -f "$path" ]; then
    echo "missing required live USB image build execution plan path: $path" >&2
    exit 1
  fi
done

scan_result="${TMPDIR:-/tmp}/cyberhive-live-usb-image-build-execution-plan-secret-scan.txt"
: > "$scan_result"
secret_pattern='BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|password[[:space:]]*=|token[[:space:]]*=|[s]ecret[[:space:]]*='

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  grep -n -E "$secret_pattern" "$path" >>"$scan_result" 2>/dev/null || true
done

if [ -s "$scan_result" ]; then
  cat "$scan_result" >&2
  echo 'potential credential material found in live USB image build execution plan scope' >&2
  exit 1
fi

sh -n scripts/validate-live-usb-image-build-execution-plan.sh

grep -n 'WB-HIVE-BOOT-0005' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'IMAGE BUILD EXECUTION PLAN ONLY' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'current-main image artifact: NOT CREATED BY THIS PLAN' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'USB write: NOT AUTHORIZED' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'hardware boot: NOT CLAIMED' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'runtime verification: NOT CLAIMED' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'deployment: NOT PERFORMED' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'ADR accepted: NO' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null

grep -n 'main source commit must be re-read before execution' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'exact source_commit must match the workflow artifact manifest' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'manual workflow dispatch is explicit image-only approval' docs/runbooks/live-usb-image-build-execution-plan.md >/dev/null

grep -n 'Future workflow dispatch:' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'operation_class: REMOTE_WRITE + COMPUTE' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'scope: manual GitHub workflow dispatch on main' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'Future build execution:' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null
grep -n 'scope: isolated GitHub-hosted runner or disposable local builder' docs/work-blocks/WB-HIVE-BOOT-0005-image-build-execution-plan.md >/dev/null

grep -n 'Required workflow dispatch:' docs/runbooks/live-usb-image-build-execution-plan.md >/dev/null
grep -n 'workflow: Live USB real image build manual' docs/runbooks/live-usb-image-build-execution-plan.md >/dev/null
grep -n 'ref: main' docs/runbooks/live-usb-image-build-execution-plan.md >/dev/null
grep -n 'approval_token: BUILD_IMAGE_ONLY_NO_USB' docs/runbooks/live-usb-image-build-execution-plan.md >/dev/null
grep -n 'run_build: true' docs/runbooks/live-usb-image-build-execution-plan.md >/dev/null
grep -n 'builder_label: github-main-<sha>-run-<run_id> or another safe label' docs/runbooks/live-usb-image-build-execution-plan.md >/dev/null

grep -n 'IMAGE BUILD EXECUTION PLAN ONLY' docs/runbooks/live-usb-image-build-execution-plan.md >/dev/null
grep -n 'IMAGE BUILD EXECUTION PLAN ONLY' docs/security/live-usb-image-build-execution-safety.md >/dev/null
grep -n 'IMAGE BUILD EXECUTION PLAN ONLY' infra/live-usb/debian-live/IMAGE-BUILD-EXECUTION-PLAN.md >/dev/null
grep -n 'current-main image artifact: NOT CREATED BY THIS PLAN' docs/security/live-usb-image-build-execution-safety.md >/dev/null
grep -n 'current-main image artifact: NOT CREATED BY THIS PLAN' infra/live-usb/debian-live/IMAGE-BUILD-EXECUTION-PLAN.md >/dev/null

grep -n 'WB-HIVE-BOOT-0005' docs/notes/WB-HIVE-BOOT-0005-source-map.md >/dev/null
grep -n 'baseline_main_commit: c854089a375f3bd644d3445e45d7d119a4f4ba08' docs/notes/WB-HIVE-BOOT-0005-source-map.md >/dev/null

grep -n '### Stage 4 — image build execution plan' infra/live-usb/build-plan.md >/dev/null
grep -n 'Status: implemented as plan by `WB-HIVE-BOOT-0005`' infra/live-usb/build-plan.md >/dev/null
grep -n '### Stage 5 — current-main image build execution' infra/live-usb/build-plan.md >/dev/null
grep -n '### Stage 6 — USB boot smoke' infra/live-usb/build-plan.md >/dev/null

workflow='.github/workflows/live-usb-image-build-execution-plan.yml'
grep -n '^name: Live USB image build execution plan$' "$workflow" >/dev/null
grep -n '^  pull_request:$' "$workflow" >/dev/null
grep -n '^  push:$' "$workflow" >/dev/null
grep -n 'scripts/validate-live-usb-image-build-execution-plan.sh' "$workflow" >/dev/null

if grep -n 'build-real-image.sh' "$workflow"; then
  echo 'execution-plan workflow must not call the real image build wrapper' >&2
  exit 1
fi
if grep -n 'BUILD_IMAGE_ONLY_NO_USB' "$workflow"; then
  echo 'execution-plan workflow must not carry the image-build approval token' >&2
  exit 1
fi
if grep -n 'docker run' "$workflow"; then
  echo 'execution-plan workflow must not run a build container' >&2
  exit 1
fi
if grep -n 'upload-artifact' "$workflow"; then
  echo 'execution-plan workflow must not upload image artifacts' >&2
  exit 1
fi

echo 'CyberHIVE live USB image build execution plan validation passed'
