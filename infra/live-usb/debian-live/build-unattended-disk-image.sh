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
. "$script_dir/config/includes.chroot/etc/cyberhive/live/config.env"
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
tar -C "$work/bundle" -cf "$bundle" \
  slot/initrd.img \
  slot/live/filesystem.squashfs \
  slot/slot.json \
  slot/vmlinuz
bundle_sha=$(sha256sum "$bundle" | awk '{print $1}')
bundle_bytes=$(wc -c <"$bundle" | tr -d ' ')
printf '%s  %s\n' "$bundle_sha" "$(basename "$bundle")" >"$bundle_sha_file"

cat >"$work/grub.cfg" <<'EOGRUB'
insmod part_gpt
insmod fat
insmod ext2
insmod env
insmod linux
insmod regexp

# Bind every boot decision to the EFI device that firmware actually loaded.
# v0.3 layout is fixed: GPT1=EFI, GPT2=A, GPT3=B, GPT4=STATE.
set boot_disk=
if [ -n "$cmdpath" ]; then
  regexp --set=1:boot_disk '^\(([^,]+),gpt1\)(/.*)?$' "$cmdpath"
fi
if [ -z "$boot_disk" ]; then
  echo "CyberHIVE: cannot prove boot EFI parent"
  sleep 30
  reboot
fi

set efi="$boot_disk,gpt1"
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
  set slotdev="$boot_disk,gpt3"
  set live_path=/slots/B/live
else
  set boot_slot=A
  set slotdev="$boot_disk,gpt2"
  set live_path=/slots/A/live
fi
set slotroot=($slotdev)/slots/$boot_slot

if [ ! -f "$slotroot/vmlinuz" -o ! -f "$slotroot/initrd.img" -o ! -f "$slotroot/live/filesystem.squashfs" ]; then
  set missing_slot="$boot_slot"
  if [ "$boot_slot" = "A" ]; then
    set boot_slot=B
    set slotdev="$boot_disk,gpt3"
    set live_path=/slots/B/live
  else
    set boot_slot=A
    set slotdev="$boot_disk,gpt2"
    set live_path=/slots/A/live
  fi
  set slotroot=($slotdev)/slots/$boot_slot
  if [ -n "$pending_slot" -a "$missing_slot" = "$pending_slot" ]; then
    set current_slot=$boot_slot
    set pending_slot=
    set previous_slot=
    set tries=
    set pending_release_id=
    save_env -f "$envfile" current_slot pending_slot previous_slot tries pending_release_id
  fi
fi

if [ ! -f "$slotroot/vmlinuz" -o ! -f "$slotroot/initrd.img" -o ! -f "$slotroot/live/filesystem.squashfs" ]; then
  echo "CyberHIVE: no bootable A/B slot found on boot EFI parent"
  sleep 30
  reboot
fi

set selected_slot="($slotdev)"
probe --fs-uuid --set=slot_uuid "$selected_slot"
if [ -z "$slot_uuid" ]; then
  echo "CyberHIVE: cannot prove selected slot filesystem UUID"
  sleep 30
  reboot
fi

set slot_uuid_match=
set slot_uuid_duplicate=
for candidate in (*); do
  set candidate_uuid=
  probe --fs-uuid --set=candidate_uuid "$candidate"
  if [ "$candidate_uuid" = "$slot_uuid" ]; then
    if [ -z "$slot_uuid_match" ]; then
      set slot_uuid_match="$candidate"
    else
      if [ "$slot_uuid_match" != "$candidate" ]; then set slot_uuid_duplicate=true; fi
    fi
  fi
done
if [ "$slot_uuid_duplicate" = true ]; then
  echo "CyberHIVE: duplicate selected slot filesystem UUID"
  sleep 30
  reboot
fi
if [ "$slot_uuid_match" != "$selected_slot" ]; then
  echo "CyberHIVE: selected slot filesystem UUID resolved ambiguously"
  sleep 30
  reboot
fi

linux "$slotroot/vmlinuz" boot=live components username=cyberhive hostname=cyberhive-live live-media=/dev/disk/by-uuid/$slot_uuid live-media-path=$live_path cyberhive.slot=$boot_slot cyberhive.slot_uuid=$slot_uuid quiet splash panic=30
initrd "$slotroot/initrd.img"
boot
EOGRUB

grub-mkstandalone -O x86_64-efi -o "$work/BOOTX64.EFI" "boot/grub/grub.cfg=$work/grub.cfg"
grub-editenv "$work/grubenv" create
grub-editenv "$work/grubenv" set current_slot=A

truncate -s 6G "$raw"
sgdisk --clear \
  --new=1:2048:+256M  --typecode=1:EF00 --change-name=1:"$CYBERHIVE_EFI_LABEL" \
  --new=2:0:+1536M    --typecode=2:8300 --change-name=2:"$CYBERHIVE_SLOT_A_LABEL" \
  --new=3:0:+1536M    --typecode=3:8300 --change-name=3:"$CYBERHIVE_SLOT_B_LABEL" \
  --new=4:0:0         --typecode=4:8300 --change-name=4:"$CYBERHIVE_STATE_LABEL" \
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
mkfs.vfat -F 32 -n "$CYBERHIVE_EFI_LABEL" "$work/efi.fs" >>"$log" 2>&1
mmd -i "$work/efi.fs" ::/EFI ::/EFI/BOOT ::/cyberhive
mcopy -i "$work/efi.fs" "$work/BOOTX64.EFI" ::/EFI/BOOT/BOOTX64.EFI
mcopy -i "$work/efi.fs" "$work/grubenv" ::/cyberhive/grubenv

truncate -s $((p2_sectors * 512)) "$work/slot-a.fs"
mke2fs -q -F -t ext4 -m 0 -L "$CYBERHIVE_SLOT_A_LABEL" -d "$work/slot-a" "$work/slot-a.fs"
truncate -s $((p3_sectors * 512)) "$work/slot-b.fs"
mke2fs -q -F -t ext4 -m 0 -L "$CYBERHIVE_SLOT_B_LABEL" -d "$work/slot-b" "$work/slot-b.fs"
truncate -s $((p4_sectors * 512)) "$work/state.fs"
mke2fs -q -F -t ext4 -m 0 -L "$CYBERHIVE_STATE_LABEL" -d "$work/state" "$work/state.fs"

dd if="$work/efi.fs" of="$raw" bs=512 seek="$p1_start" conv=notrunc,sparse status=none
dd if="$work/slot-a.fs" of="$raw" bs=512 seek="$p2_start" conv=notrunc,sparse status=none
dd if="$work/slot-b.fs" of="$raw" bs=512 seek="$p3_start" conv=notrunc,sparse status=none
dd if="$work/state.fs" of="$raw" bs=512 seek="$p4_start" conv=notrunc,sparse status=none
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
  "efi_label": "$CYBERHIVE_EFI_LABEL",
  "slot_a_label": "$CYBERHIVE_SLOT_A_LABEL",
  "slot_b_label": "$CYBERHIVE_SLOT_B_LABEL",
  "state_label": "$CYBERHIVE_STATE_LABEL",
  "initial_slot": "A",
  "usb_written": false,
  "hardware_booted": false,
  "runtime_verified": false
}
EOMANIFEST

printf 'CyberHIVE unattended disk image build passed\n' | tee -a "$log"
printf 'compressed_image=%s\nraw_sha256=%s\nslot_bundle=%s\n' "$gz" "$raw_sha" "$bundle"
