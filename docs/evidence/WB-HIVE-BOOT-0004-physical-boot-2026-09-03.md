# WB-HIVE-BOOT-0004 Physical Media + Boot Evidence — 2026-09-03

## Evidence identity

Source image:

```text
cyberhive-live-usb-v0.1-amd64-20260903T173947Z.iso
SHA-256 a93778f299031a0eab340f75e95ed600c5cef315c0678929b36b093ccb023b49
bytes 861929472
source PR #27 head 63c14dba7fd28b8a0d53c23bbda766b06d950260
source workflow run 33785844714
```

## Media write receipt

Target was independently identified before write as one removable external USB device:

```text
/dev/disk2
Device / Media Name: Flash Reader
Protocol: USB
Disk Size: 63864569856 bytes
Removable Media: Removable
Virtual: No
```

Write result:

```text
102+1 records in
102+1 records out
861929472 bytes transferred
DD_RC=0
```

Independent readback:

```text
cmp -n 861929472 <source.iso> /dev/rdisk2
CMP_RC=0
```

The device was ejected after verification.

## Physical boot observation

A user-provided photograph showed a physical boot into:

```text
Debian GNU/Linux 12 cyberhive-live tty1
Linux cyberhive-live 6.1.0-52-amd64 ... x86_64
CyberHIVE Live USB
cyberhive@cyberhive-live:~$
```

A later photograph showed network state and the SSH gap:

```text
enx9cebe8a235ea UP 192.168.1.122/24
systemctl is-active ssh -> inactive
systemctl start ssh -> Unit ssh.service not found
systemctl start sshd -> Unit sshd.service not found
```

This is the direct trigger for `WB-HIVE-BOOT-0005`.

## Photograph identity

The conversation-provided PNG used for the network/SSH observation had:

```text
SHA-256 0168952d83020b82e6d35fdcff907adbab96701d29f99c65577f8257b7eec7f6
PNG 1524 x 2048 RGBA
```

The binary photograph is not committed by this receipt; the digest preserves the evidence identity of the inspected file.

## Verdict

```text
IMAGE_BUILD=PASS
MEDIA_WRITE=PASS
WRITEBACK_COMPARE=PASS
PHYSICAL_BOOT=PASS
LIVE_SHELL=PASS
NETWORK_DHCP=OBSERVED
SSH_SERVER=FAIL/MISSING_IN_V0.1
HOST_DISK_SAFETY_RUNTIME=NOT_YET_CLOSED
DEVBRIDGE_MCP=NOT_ENABLED
DEPLOYMENT=NOT_PERFORMED
ADR_ACCEPTANCE=NOT_GRANTED
```
