#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-live-health"
COMMIT = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-boot-commit"

live = LIVE.read_text(encoding="utf-8")
commit = COMMIT.read_text(encoding="utf-8")

assert "cyberhive-health-classify" in live
assert '"health":$health' in live or "health:$health" in live
assert ".local_safe" in live
assert "status='ok'" in live
assert "status='degraded'" in live

start = commit.index("health_ok='false'")
end = commit.index('if [ "$health_ok" = \'true\' ]; then', start)
gate = commit[start:end]

assert "cyberhive-live-health" in gate
assert ".health.local_safe == \"pass\"" in gate
assert "tailscale status" not in gate
assert "systemctl is-active --quiet tailscaled.service" not in gate

print("CyberHIVE offline-safe boot health contract validation passed")
