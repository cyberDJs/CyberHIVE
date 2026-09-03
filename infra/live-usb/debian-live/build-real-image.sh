#!/bin/sh
set -eu

approval="${CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL:-}"
if [ "$approval" != "BUILD_IMAGE_ONLY_NO_USB" ]; then
  echo 'refusing real image build: set CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL=BUILD_IMAGE_ONLY_NO_USB' >&2
  exit 2
fi

hash_tool=''
if command -v sha256sum >/dev/null 2>&1; then
  hash_tool='sha256sum'
elif command -v shasum >/dev/null 2>&1; then
  hash_tool='shasum'
elif command -v openssl >/dev/null 2>&1; then
  hash_tool='openssl'
else
  echo 'refusing real image build: no SHA-256 tool available' >&2
  exit 5
fi

raw_builder_label="${CYBERHIVE_REAL_IMAGE_BUILDER_LABEL:-operator-or-runner-label}"
if [ -z "$raw_builder_label" ] || [ "${#raw_builder_label}" -gt 80 ]; then
  echo 'invalid builder label: use 1-80 characters from A-Z a-z 0-9 . _ : @ -' >&2
  exit 2
fi
case "$raw_builder_label" in
  *[!A-Za-z0-9._:@-]*) echo 'invalid builder label: use 1-80 characters from A-Z a-z 0-9 . _ : @ -' >&2; exit 2 ;;
esac

sha256_file() {
  case "$hash_tool" in
    sha256sum) sha256sum "$1" | awk '{print $1}' ;;
    shasum) shasum -a 256 "$1" | awk '{print $1}' ;;
    openssl) openssl dgst -sha256 -r "$1" | awk '{print $1}' ;;
    *) echo 'internal error: SHA-256 tool not configured' >&2; exit 5 ;;
  esac
}

json_string() {
  printf '%s' "$1" | tr -d '\r\n' | sed 's/\\/\\\\/g; s/"/\\"/g'
}

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH= cd "$script_dir/../../.." && pwd)
live_dir="$repo_root/infra/live-usb/debian-live"
out_dir="$repo_root/.cyberhive-live-real-build"
brand_source="$repo_root/assets/brand/runtime/cyberdjs-cyberhive-boot.svg"
source_commit='UNKNOWN'
if command -v git >/dev/null 2>&1 && git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  source_commit=$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || printf '%s' 'UNKNOWN')
fi

stamp=$(date -u +%Y%m%dT%H%M%SZ)
build_id="cyberhive-live-usb-v0.2-amd64-$stamp"
work_dir="$out_dir/$build_id.work"
build_dir="$work_dir/debian-live"
image_name="$build_id.iso"
image_path="$out_dir/$image_name"
image_sha_path="$out_dir/$build_id.sha256"
manifest_path="$out_dir/$build_id.manifest.json"
manifest_sha_path="$manifest_path.sha256"
build_log_name="$build_id.build-log.txt"
build_log_path="$out_dir/$build_log_name"
package_manifest_name='UNKNOWN'
package_manifest_sha='UNKNOWN'
package_manifest_path=''
brand_sha='UNKNOWN'

mkdir -p "$out_dir" "$build_dir"
: > "$build_log_path"

builder_label=$(json_string "$raw_builder_label")
builder_os=$(json_string "$(uname -a 2>/dev/null || printf '%s' UNKNOWN)")
build_tool_version='UNKNOWN'
if command -v lb >/dev/null 2>&1; then
  build_tool_version=$(json_string "$(lb --version 2>/dev/null | head -n 1 || printf '%s' UNKNOWN)")
fi
if [ -f "$brand_source" ]; then
  brand_sha=$(sha256_file "$brand_source")
fi

write_manifest() {
  status="$1"; image_created="$2"; image_filename_json="$3"; image_bytes_json="$4"; image_sha_json="$5"
  build_log_sha=$(sha256_file "$build_log_path")
  cat >"$manifest_path" <<EOF
{
  "schema": "cyberhive.live.real_build.v0",
  "status": "$status",
  "mode": "real-build",
  "live_version": "0.2.0-dev",
  "source_commit": "$source_commit",
  "candidate": "debian-live",
  "candidate_path": "infra/live-usb/debian-live",
  "boot_brand_source": "assets/brand/runtime/cyberdjs-cyberhive-boot.svg",
  "boot_brand_sha256": "$brand_sha",
  "builder_identity_label": "$builder_label",
  "builder_os": "$builder_os",
  "build_tool": "live-build",
  "build_tool_version": "$build_tool_version",
  "output_directory": ".cyberhive-live-real-build/",
  "image_filename": $image_filename_json,
  "image_bytes": $image_bytes_json,
  "image_sha256": $image_sha_json,
  "build_log_filename": "$build_log_name",
  "build_log_sha256": "$build_log_sha",
  "package_manifest_filename": "$package_manifest_name",
  "package_manifest_sha256": "$package_manifest_sha",
  "build_executed": true,
  "image_created": $image_created,
  "usb_written": false,
  "hardware_booted": false,
  "runtime_verified": false,
  "devbridge_enabled": false,
  "mcp_enabled": false,
  "deployment_performed": false,
  "adr_accepted": false
}
EOF
  manifest_sha=$(sha256_file "$manifest_path")
  printf '%s  %s\n' "$manifest_sha" "$(basename "$manifest_path")" >"$manifest_sha_path"
}

cp -R "$live_dir/." "$build_dir/"

if ! command -v lb >/dev/null 2>&1; then
  echo 'live-build tool lb is not available' >>"$build_log_path"
  write_manifest 'failed' 'false' 'null' 'null' 'null'
  echo 'CyberHIVE real image build failed: lb missing' >&2
  echo "manifest: $manifest_path"
  exit 3
fi
if [ ! -f "$brand_source" ]; then
  echo 'CyberHIVE boot brand source is missing' >>"$build_log_path"
  write_manifest 'failed' 'false' 'null' 'null' 'null'
  exit 6
fi
if ! command -v rsvg-convert >/dev/null 2>&1; then
  echo 'CyberHIVE boot brand renderer rsvg-convert is missing' >>"$build_log_path"
  write_manifest 'failed' 'false' 'null' 'null' 'null'
  exit 6
fi

prepare_boot_branding() {
  prepared=0
  mkdir -p "$build_dir/config/bootloaders"

  # live-build 1:20230502 uses config/bootloaders/grub-pc as the shared
  # configuration source for both grub-pc and grub-efi. Targeting a
  # non-existent grub-efi theme directory leaves UEFI boots unbranded.
  for bootloader in isolinux syslinux_common grub-pc; do
    default_theme="/usr/share/live/build/bootloaders/$bootloader"
    custom_theme="$build_dir/config/bootloaders/$bootloader"
    if [ -d "$default_theme" ]; then
      rm -rf "$custom_theme"
      cp -R "$default_theme" "$custom_theme"
      rsvg-convert --width 640 --height 480 "$brand_source" >"$custom_theme/splash.png"
      rm -f "$custom_theme/splash.svg"
      prepared=$((prepared + 1))
    fi
  done

  [ -f "$build_dir/config/bootloaders/grub-pc/splash.png" ] || return 1
  [ "$prepared" -gt 0 ] || return 1
  printf 'prepared CyberHIVE boot branding for %s bootloader theme(s), including grub-pc shared EFI source\n' "$prepared" >>"$build_log_path"
}

if ! prepare_boot_branding; then
  echo 'CyberHIVE bootloader theme preparation failed' >>"$build_log_path"
  write_manifest 'failed' 'false' 'null' 'null' 'null'
  exit 6
fi

build_status='ok'
(
  cd "$build_dir"
  sh auto/config
  lb build
) >>"$build_log_path" 2>&1 || build_status='failed'

# Verify the rendered brand actually reached the GRUB tree used by EFI boot.
if [ "$build_status" = 'ok' ]; then
  expected_grub_splash="$build_dir/config/bootloaders/grub-pc/splash.png"
  built_grub_splash="$build_dir/binary/boot/grub/splash.png"
  if [ ! -f "$built_grub_splash" ]; then
    echo 'CyberHIVE EFI branding verification failed: binary/boot/grub/splash.png missing' >>"$build_log_path"
    build_status='failed'
  else
    expected_grub_sha=$(sha256_file "$expected_grub_splash")
    built_grub_sha=$(sha256_file "$built_grub_splash")
    if [ "$expected_grub_sha" != "$built_grub_sha" ]; then
      echo 'CyberHIVE EFI branding verification failed: GRUB splash hash mismatch' >>"$build_log_path"
      build_status='failed'
    else
      printf 'CyberHIVE EFI branding verified: %s\n' "$built_grub_sha" >>"$build_log_path"
    fi
  fi
fi

built_iso=''
for candidate in "$build_dir"/live-image-*.iso "$build_dir"/*.iso; do
  if [ -f "$candidate" ]; then built_iso="$candidate"; break; fi
done

if [ "$build_status" = 'ok' ] && [ -n "$built_iso" ]; then
  cp "$built_iso" "$image_path"
  image_hash=$(sha256_file "$image_path")
  image_bytes=$(wc -c <"$image_path" | tr -d ' ')
  printf '%s  %s\n' "$image_hash" "$image_name" >"$image_sha_path"
  if [ -f "$build_dir/binary.packages" ]; then
    package_manifest_name="$build_id.packages.txt"
    package_manifest_path="$out_dir/$package_manifest_name"
    cp "$build_dir/binary.packages" "$package_manifest_path"
    package_manifest_sha=$(sha256_file "$package_manifest_path")
  fi
  write_manifest 'ok' 'true' "\"$image_name\"" "$image_bytes" "\"$image_hash\""
  echo 'CyberHIVE real image build gate passed'
  echo "image: $image_path"
  echo "manifest: $manifest_path"
  exit 0
fi

write_manifest 'failed' 'false' 'null' 'null' 'null'
echo 'CyberHIVE real image build gate failed' >&2
echo "manifest: $manifest_path"
exit 4
