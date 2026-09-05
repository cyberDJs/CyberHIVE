#!/bin/sh

cyberhive_live_medium_device() {
  for target in /run/live/medium /lib/live/mount/medium; do
    source=$(findmnt -nr -o SOURCE --target "$target" 2>/dev/null || true)
    [ -n "$source" ] || continue
    source=$(printf '%s' "$source" | sed 's/\[.*$//')
    case "$source" in
      /dev/*)
        source=$(readlink -f "$source" 2>/dev/null || printf '%s' "$source")
        [ -b "$source" ] || continue
        printf '%s\n' "$source"
        return 0
        ;;
    esac
  done
  return 1
}

cyberhive_parent_device() {
  dev=$1
  pk=$(lsblk -ndo PKNAME "$dev" 2>/dev/null | head -n 1 || true)
  [ -n "$pk" ] || return 1
  printf '/dev/%s\n' "$pk"
}

cyberhive_require_usb_parent() {
  parent=$1
  [ -b "$parent" ] || return 1
  [ "$(lsblk -ndo TRAN "$parent" 2>/dev/null | head -n 1 || true)" = 'usb' ]
}

cyberhive_partition_on_parent_by_label() {
  parent=$1
  label=$2
  matches=$(lsblk -nrpo NAME,TYPE,LABEL "$parent" 2>/dev/null | awk -v want="$label" '$2 == "part" && $3 == want {print $1}')
  count=$(printf '%s\n' "$matches" | awk 'NF {n++} END {print n+0}')
  [ "$count" -eq 1 ] || return 1
  printf '%s\n' "$matches"
}

cyberhive_slot_label() {
  case "$1" in
    A) printf '%s\n' "$CYBERHIVE_SLOT_A_LABEL" ;;
    B) printf '%s\n' "$CYBERHIVE_SLOT_B_LABEL" ;;
    *) return 1 ;;
  esac
}

cyberhive_verify_live_slot() {
  slot=$1
  dev=$2
  expected=$(cyberhive_slot_label "$slot") || return 1
  actual=$(blkid -s LABEL -o value "$dev" 2>/dev/null || true)
  [ "$actual" = "$expected" ]
}
