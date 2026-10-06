#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-live-health"
CLASSIFIER = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-health-classify"
GUARDIAN = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-guardian"

live = LIVE.read_text()
classifier = CLASSIFIER.read_text()
guardian = GUARDIAN.read_text()

assert "/usr/local/bin/cyberhive-management-firewall-attest" in live
assert "management_firewall" in live
assert '"management_firewall"' in classifier
assert '"management-firewall"' in classifier
assert "cyberhive-management-firewall-attest" in guardian
assert "management-firewall-unattested" in guardian

print("CyberHIVE firewall attestation health/Guardian integration contract passed")
