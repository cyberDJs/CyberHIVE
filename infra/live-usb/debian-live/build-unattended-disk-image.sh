#!/bin/sh
set -eu

approval="${CYBERHIVE_REAL_IMAGE_BUILD_APPROVAL:-}"
if [ "$approval" != 'BUILD_IMAGE_ONLY_NO_USB' ]; then
  echo 'refusing unattended disk image build: explicit image-only approval token missing' >&2
  exit 2
fi

for cmd in sha256sum xorriso sgdisk mkfs.vfat mmd mcopy mke2fs grub-mkstandalone grub-editenv tar gzip dd truncate awk sed grep find wc; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "missing build dependency: $cmd" >&2; exit 3; }
done

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH= cd "$script_dir/../../.." && pwd)
out_dir="$repo_root/.cyberhive-live-real-build"
source_commit='UNKNOWN'
if command -v git >/dev/null 2>&1 && git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  source_commit=$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || printf UNKNOWN)
fi

iso=$(ls -1t "$out_dir"/*.iso 2>/dev/null | head -n 1 || true)
[ -n "$iso" ] && [ -f "$iso" ] || { echo 'no approved ISO exists for unattended disk wrapper' >&2; exit 4; }
iso_sha=$(sha256sum "$iso" | awk '{print $1}')
iso_bytes=$(wc -c <"$iso" | tr -d ' ')
stamp=$(date -u +%Y%m%dT%H%M%SZ)
build_id="cyberhive-unattended-v0.3-amd64-$stamp"
work="$out_dir/$build_id.work"
raw="$out_dir/$build_id.img"
gz="$raw.gz"
raw_sha_file="$out_dir/$build_id.img.sha256"
gz_sha_file="$out_dir/$build_id.img.gz.sha256"
bundle="$out_dir/$build_id.slot.tar"
bundle_sha_file="$bundle.sha256"
manifest="$out_dir/$build_id.manifest.json"
log="$out_dir/$build_id.build-log.txt"
rm -rf "$work"
mkdir -p \
  "$work/slot-a/slots/A/live" \
  "$work/slot-b/slots/B" \
  "$work/state/state/network" \
  "$work/state/state/tailscale" \
  "$work/state/state/ssh/host_keys" \
  "$work/state/state/ota" \
  "$work/state/state/evidence" \
  "$work/state/cache" \
  "$work/iso-live" \
  "$work/bundle/slot/live"
: >"$log"

xorriso -osirrox on -indev "$iso" -extract /live "$work/iso-live" >>"$log" 2>&1
kernel=$(find "$work/iso-live" -maxdepth 2 -type f -name 'vmlinuz*' | head -n 1 || true)
initrd=$(find "$work/iso-live" -maxdepth 2 -type f -name 'initrd*' | head -n 1 || true)
squash=$(find "$work/iso-live" -maxdepth 2 -type f -name 'filesystem.squashfs' | head -n 1 || true)
[ -s "$kernel" ] && [ -s "$initrd" ] && [ -s "$squash" ] || { echo 'ISO live payload incomplete' >&2; exit 5; }
cp "$kernel" "$work/slot-a/slots/A/vmlinuz"
cp "$initrd" "$work/slot-a/slots/A/initrd.img"
cp "$squash" "$work/slot-a/slots/A/live/filesystem.squashfs"
cat >"$work/slot-a/slots/A/slot.json" <<EOSLOT
{"schema":"cyberhive.slot.v1","slot":"A","live_version":"0.3.0-dev","source_commit":"$source_commit","source_iso_sha256":"$iso_sha"}
EOSLOT

cp "$work/slot-a/slots/A/vmlinuz" "$work/bundle/slot/vmlinuz"
cp "$work/slot-a/slots/A/initrd.img" "$work/bundle/slot/initrd.img"
cp "$work/slot-a/slots/A/live/filesystem.squashfs" "$work/bundle/slot/live/filesystem.squashfs"
cp "$work/slot-a/slots/A/slot.json" "$work/bundle/slot/slot.json"
tar -C "$work/bundle" -cf "$bundle" slot
bundle_sha=$(sha256sum "$bundle" | awk '{print $1}')
bundle_bytes=$(wc -c <"$bundle" | tr -d ' ')
printf '%s  %s\n' "$bundle_sha" "$(basename "$bundle")" >"$bundle_sha_file"

cat >"$work/grub.cfg" <<'EOGRUB'
insmod part_gpt
insmod fat
insmod ext2
insmod search
insmod search_label
insmod env
insmod linux

search --no-floppy --label CYBERHIVE_EFI --set=efi
set envfile=($efi)/cyberhive/grubenv
if [ -f "$envfile" ]; then load_env -f "$envfile"; fi
if [ -z "$current_slot" ]; then set current_slot=A; fi
set boot_slot=$current_slot

if [ -n "$pending_slot" ]; then
  if [ "$tries" = "1" ]; then
    set boot_slot=$pending_slot
    set tries=0
    save_env -f "$envfile" tries
  else
    if [ -n "$previous_slot" ]; then set boot_slot=$previous_slot; else set boot_slot=$current_slot; fi
    set current_slot=$boot_slot
    set pending_slot=
    set previous_slot=
    set tries=
    set pending_release_id=
    save_env -f "$envfile" current_slot pending_slot previous_slot tries pending_release_id
  fi
fi

if [ "$boot_slot" = "B" ]; then
  set slot_label=CYBERHIVE_B
  set live_path=/slots/B/live
else
  set boot_slot=A
  set slot_label=CYBERHIVE_A
  set live_path=/slots/A/live
fi
search --no-floppy --label $slot_label --set=slotdev
set slotroot=($slotdev)/slots/$boot_slot

if [ ! -f "$slotroot/vmlinuz" -o ! -f "$slotroot/initrd.img" -o ! -f "$slotroot/live/filesystem.squashfs" ]; then
  if [ "$boot_slot" = "A" ]; then
    set boot_slot=B
    set slot_label=CYBERHIVE_B
    set live_path=/slots/B/live
  else
    set boot_slot=A
    set slot_label=CYBERHIVE_A
    set live_path=/slots/A/live
  fi
  search --no-floppy --label $slot_label --set=slotdev
  set slotroot=($slotdev)/slots/$boot_slot
fi

if [ ! -f "$slotroot/vmlinuz" -o ! -f "$slotroot/initrd.img" -o ! -f "$slotroot/live/filesystem.squashfs" ]; then
  echo "CyberHIVE: no bootable A/B slot found"
  sleep 30
  reboot
fi

linux "$slotroot/vmlinuz" boot=live components username=cyberhive hostname=cyberhive-live live-media-path=$live_path cyberhive.slot=$boot_slot quiet splash panic=30
initrd "$slotroot/initrd.img"
boot
EOGRUB

grub-mkstandalone -O x86_64-efi -o "$work/BOOTX64.EFI" "boot/grub/grub.cfg=$work/grub.cfg"
grub-editenv "$work/grubenv" create
grub-editenv "$work/grubenv" set current_slot=A

# 6 GiB bootstrap image:
# p1 256 MiB stable EFI, p2/p3 1536 MiB A/B slots, p4 dedicated persistent STATE.
truncate -s 6G "$raw"
sgdisk --clear \
  --new=1:2048:+256M  --typecode=1:EF00 --change-name=1:CYBERHIVE_EFI \
  --new=2:0:+1536M    --typecode=2:8300 --change-name=2:CYBERHIVE_A \
  --new=3:0:+1536M    --typecode=3:8300 --change-name=3:CYBERHIVE_B \
  --new=4:0:0         --typecode=4:8300 --change-name=4:CYBERHIVE_STATE \
  "$raw" >>"$log" 2>&1

part_info() {
  n=$1
  sgdisk -i "$n" "$raw" | awk '/First sector:/ {first=$3} /Last sector:/ {last=$3} END {print first, last-first+1}'
}
set -- $(part_info 1); p1_start=$1; p1_sectors=$2
set -- $(part_info 2); p2_start=$1; p2_sectors=$2
set -- $(part_info 3); p3_start=$1; p3_sectors=$2
set -- $(part_info 4); p4_start=$1; p4_sectors=$2

truncate -s $((p1_sectors * 512)) "$work/efi.fs"
mkfs.vfat -F 32 -n CYBERHIVE_EFI "$work/efi.fs" >>"$log" 2>&1
mmd -i "$work/efi.fs" ::/EFI ::/EFI/BOOT ::/cyberhive
mcopy -i "$work/efi.fs" "$work/BOOTX64.EFI" ::/EFI/BOOT/BOOTX64.EFI
mcopy -i "$work/efi.fs" "$work/grubenv" ::/cyberhive/grubenv

truncate -s $((p2_sectors * 512)) "$work/slot-a.fs"
mke2fs -q -F -t ext4 -m 0 -L CYBERHIVE_A -d "$work/slot-a" "$work/slot-a.fs"
truncate -s $((p3_sectors * 512)) "$work/slot-b.fs"
mke2fs -q -F -t ext4 -m 0 -L CYBERHIVE_B -d "$work/slot-b" "$work/slot-b.fs"
truncate -s $((p4_sectors * 512)) "$work/state.fs"
mke2fs -q -F -t ext4 -m 0 -L CYBERHIVE_STATE -d "$work/state" "$work/state.fs"

dd if="$work/efi.fs" of="$raw" bs=512 seek="$p1_start" conv=notrunc status=none
dd if="$work/slot-a.fs" of="$raw" bs=512 seek="$p2_start" conv=notrunc status=none
dd if="$work/slot-b.fs" of="$raw" bs=512 seek="$p3_start" conv=notrunc status=none
dd if="$work/state.fs" of="$raw" bs=512 seek="$p4_start" conv=notrunc status=none
sync

raw_sha=$(sha256sum "$raw" | awk '{print $1}')
raw_bytes=$(wc -c <"$raw" | tr -d ' ')
printf '%s  %s\n' "$raw_sha" "$(basename "$raw")" >"$raw_sha_file"
gzip -1 -c "$raw" >"$gz"
gz_sha=$(sha256sum "$gz" | awk '{print $1}')
gz_bytes=$(wc -c <"$gz" | tr -d ' ')
printf '%s  %s\n' "$gz_sha" "$(basename "$gz")" >"$gz_sha_file"
rm -f "$raw"

cat >"$manifest" <<EOMANIFEST
{
  "schema": "cyberhive.unattended.disk_build.v1",
  "status": "ok",
  "live_version": "0.3.0-dev",
  "source_commit": "$source_commit",
  "source_iso_filename": "$(basename "$iso")",
  "source_iso_bytes": $iso_bytes,
  "source_iso_sha256": "$iso_sha",
  "disk_image_gzip_filename": "$(basename "$gz")",
  "disk_image_gzip_bytes": $gz_bytes,
  "disk_image_gzip_sha256": "$gz_sha",
  "disk_image_raw_bytes": $raw_bytes,
  "disk_image_raw_sha256": "$raw_sha",
  "slot_bundle_filename": "$(basename "$bundle")",
  "slot_bundle_bytes": $bundle_bytes,
  "slot_bundle_sha256": "$bundle_sha",
  "efi_label": "CYBERHIVE_EFI",
  "slot_a_label": "CYBERHIVE_A",
  "slot_b_label": "CYBERHIVE_B",
  "state_label": "CYBERHIVE_STATE",
  "initial_slot": "A",
  "usb_written": false,
  "hardware_booted": false,
  "runtime_verified": false
}
EOMANIFEST

printf 'CyberHIVE unattended disk image build passed\n' | tee -a "$log"
printf 'compressed_image=%s\nraw_sha256=%s\nslot_bundle=%s\n' "$gz" "$raw_sha" "$bundle"
