#!/usr/bin/env python3
"""Fail closed when the image build cannot meet headless OOB boot readiness.

Static preflight is necessary but NOT a substitute for a QEMU/OVMF EFI boot
and hardware AP/onboarding test. This must not mark the feature verified.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
builder = (ROOT / "infra/live-usb/debian-live/build-unattended-disk-image.sh").read_text()
active_builder = "\n".join(
    line for line in builder.splitlines() if not line.lstrip().startswith("#")
)
provisioner = (ROOT / "scripts/provision-cyberhive-oob-credentials.py").read_text()
onboard = (ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-oob-onboard").read_text()
network = (ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-oob-network").read_text()
errors = []

for forbidden in (
    "*** CYBERHIVE DIAGNOSTIC BUILD ***",
    "systemd.log_level=debug",
    "rd.emergency=shell",
    "rd.debug",
    "panic=-1",
):
    if forbidden in active_builder:
        errors.append("release image still contains active diagnostic GRUB setting: " + forbidden)

for marker in (
    "grub-mkstandalone",
    "BOOTX64.EFI",
    "boot/grub/grub.cfg=",
    "vmlinuz",
    "initrd.img",
    "filesystem.squashfs",
):
    if marker not in builder:
        errors.append("missing EFI boot evidence: " + marker)

for marker in (
    "::/cyberhive/slots/A/vmlinuz",
    "::/cyberhive/slots/A/initrd.img",
    "set kernroot=($efi)/cyberhive/slots/$boot_slot",
    'linux "$kernroot/vmlinuz"',
    'initrd "$kernroot/initrd.img"',
    '"efi_kernel_payload": true',
):
    if marker not in builder:
        errors.append("missing EFI kernel-payload repair contract: " + marker)

if 'linux "$slotroot/vmlinuz"' in active_builder or 'initrd "$slotroot/initrd.img"' in active_builder:
    errors.append("active GRUB still loads kernel/initrd directly from ext4 slotroot")

for marker in ("--state-dir", "--setup-card", "wifi_qr_payload"):
    if marker not in provisioner:
        errors.append("missing offline credential handoff: " + marker)

if "10.42.0.1" not in onboard or "def apply_wifi" not in onboard:
    errors.append("AP portal contract missing")
if "FALLBACK_SECONDS" not in network:
    errors.append("network fallback delay contract missing")

if errors:
    raise SystemExit("OOB release contract FAIL:\n- " + "\n- ".join(errors))
print("Static OOB release preflight PASS; EFI boot and AP hardware verification still required")
