#!/bin/sh
set -eu

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH= cd "$script_dir/../../.." && pwd)
live_dir="$repo_root/infra/live-usb/debian-live"
out_dir="${CYBERHIVE_LIVE_DRY_RUN_DIR:-$repo_root/.cyberhive-live-build-dry-run}"
manifest="$out_dir/manifest.json"
config_env="$live_dir/config/includes.chroot/etc/cyberhive/live/config.env"
live_version=$(sed -n 's/^CYBERHIVE_LIVE_VERSION="\([^"]*\)"/\1/p' "$config_env")
[ -n "$live_version" ] || { echo 'CYBERHIVE_LIVE_VERSION missing' >&2; exit 1; }

base_required_paths='auto/config
config/package-lists/cyberhive-live.list.chroot
config/includes.chroot/etc/cyberhive/live/config.env
config/includes.chroot/usr/local/bin/cyberhive-live-health
config/includes.chroot/usr/local/bin/cyberhive-role-selector
config/includes.chroot/usr/local/bin/cyberhive-inventory
config/includes.chroot/etc/systemd/system/cyberhive-live-agent.service
config/includes.chroot/usr/lib/tmpfiles.d/cyberhive-live.conf
config/hooks/live/001-cyberhive-live-skeleton.hook.chroot'

extra_required_paths=''
case "$live_version" in
  0.1.*) ;;
  0.2.*)
    extra_required_paths='config/includes.chroot/usr/local/sbin/cyberhive-onboarding-init
config/includes.chroot/usr/local/bin/cyberhive-welcome
config/includes.chroot/usr/local/bin/cyberhive-web
config/includes.chroot/usr/local/bin/cyberhive-host-disk-guard
config/includes.chroot/usr/local/bin/cyberhive-support-bundle
config/includes.chroot/etc/systemd/system/cyberhive-onboarding-init.service
config/includes.chroot/etc/systemd/system/cyberhive-web.service
config/includes.chroot/etc/systemd/system/cyberhive-host-disk-guard.service'
    ;;
  *) echo "unsupported live dry-run policy version: $live_version" >&2; exit 1 ;;
esac

required_paths="$base_required_paths"
if [ -n "$extra_required_paths" ]; then
  required_paths="$required_paths
$extra_required_paths"
fi

printf '%s\n' "$required_paths" | while IFS= read -r path; do
  [ -n "$path" ] || continue
  if [ ! -f "$live_dir/$path" ]; then
    echo "missing live USB input: infra/live-usb/debian-live/$path" >&2
    exit 1
  fi
done

grep -R -n 'CYBERHIVE_DEVBRIDGE_DEFAULT="disabled"' "$live_dir" >/dev/null
grep -R -n 'CYBERHIVE_MCP_DEFAULT="disabled"' "$live_dir" >/dev/null
grep -R -n 'CYBERHIVE_HOST_DISK_WRITE_DEFAULT="disabled"' "$live_dir" >/dev/null

case "$live_version" in
  0.1.*)
    if grep -R -n '^avahi-daemon$' "$live_dir/config/package-lists" >/tmp/cyberhive-live-dry-run-discovery-scan.txt 2>/dev/null; then
      cat /tmp/cyberhive-live-dry-run-discovery-scan.txt >&2
      echo 'local discovery daemon must not be present in v0.1 package seed' >&2
      exit 1
    fi
    grep -R -n 'DevBridge/MCP: disabled' "$live_dir" >/dev/null
    grep -R -n 'Host disk writes: disabled by default' "$live_dir" >/dev/null
    ;;
  0.2.*)
    grep -R -n '^avahi-daemon$' "$live_dir/config/package-lists" >/dev/null
    grep -R -n 'CYBERHIVE_REMOTE_HELP_DEFAULT="disabled"' "$live_dir" >/dev/null
    ;;
esac

source_commit='UNKNOWN'
if command -v git >/dev/null 2>&1 && git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  source_commit=$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || printf '%s' 'UNKNOWN')
fi

live_build_tool='missing'
if command -v lb >/dev/null 2>&1; then
  live_build_tool='available'
fi

checked_paths=$(printf '%s\n' "$required_paths" | awk 'NF {count++} END {print count+0}')
mkdir -p "$out_dir"

cat >"$manifest" <<EOF
{
  "schema": "cyberhive.live.build_dry_run.v0",
  "status": "ok",
  "mode": "dry-run",
  "live_version": "$live_version",
  "source_commit": "$source_commit",
  "candidate": "debian-live",
  "candidate_path": "infra/live-usb/debian-live",
  "live_build_tool": "$live_build_tool",
  "checked_paths": $checked_paths,
  "build_executed": false,
  "iso_created": false,
  "usb_written": false,
  "runtime_verified": false,
  "devbridge_enabled": false,
  "mcp_enabled": false,
  "host_disk_write_enabled": false
}
EOF

printf 'CyberHIVE Live USB build dry-run passed for %s\n' "$live_version"
printf 'manifest: %s\n' "$manifest"
printf 'live_build_tool: %s\n' "$live_build_tool"
