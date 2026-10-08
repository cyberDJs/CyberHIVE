#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHROOT = ROOT / "infra/live-usb/debian-live/config/includes.chroot"
SERVICE = CHROOT / "etc/systemd/system/cyberhive-guardian.service"
TIMER = CHROOT / "etc/systemd/system/cyberhive-guardian.timer"
GUARDIAN = CHROOT / "usr/local/sbin/cyberhive-guardian"
PERSIST = CHROOT / "usr/local/sbin/cyberhive-persist-init"
HOOK = ROOT / "infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot"

assert SERVICE.is_file(), f"missing service: {SERVICE}"
assert TIMER.is_file(), f"missing timer: {TIMER}"

service = SERVICE.read_text()
timer = TIMER.read_text()
guardian = GUARDIAN.read_text()
persist = PERSIST.read_text()
hook = HOOK.read_text()

assert "Requires=cyberhive-persist-init.service" in service
assert "After=cyberhive-persist-init.service" in service
assert "ExecStart=/usr/local/sbin/cyberhive-guardian" in service
assert "Type=oneshot" in service
assert "WantedBy=multi-user.target" not in service
assert "Wants=NetworkManager.service" not in service
assert "Wants=NetworkManager.service tailscaled.service" not in service
assert "tailscaled.service" not in next(line for line in service.splitlines() if line.startswith("After="))

assert "OnBootSec=1min" in timer
assert "OnUnitActiveSec=1min" in timer
assert "RandomizedDelaySec=5s" in timer
assert "Persistent=false" in timer
assert "Unit=cyberhive-guardian.service" in timer
assert "WantedBy=timers.target" in timer
assert "systemctl enable cyberhive-guardian.timer" in hook

assert '"$persist/state/guardian"' in persist
assert 'chmod 0700' in persist and '"$persist/state/guardian"' in persist

for forbidden in (
    "grub-editenv",
    "systemctl reboot",
    "systemctl poweroff",
    "reboot(",
    '["reboot"]',
    "CYBER_RECOVERY",
):
    assert forbidden not in guardian, forbidden

assert "MAX_ATTEMPTS = 3" in guardian
assert "WINDOW_SECONDS = 600" in guardian
assert "MIN_INTERVAL_SECONDS = 60" in guardian
assert "CIRCUIT_SECONDS = 900" in guardian

print("CyberHIVE Guardian systemd/persistence wiring contract passed")
