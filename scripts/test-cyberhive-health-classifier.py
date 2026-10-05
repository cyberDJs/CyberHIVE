#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-health-classify"


def classify(**overrides):
    base = {
        "onboarding_service": "active",
        "ssh_service": "active",
        "web_service": "active",
        "mdns_service": "active",
        "host_disk_guard": "pass",
        "persistence": "usb-state",
        "persistence_state": "mounted:/dev/sdb4:/dev/sdb:A",
        "lan_ip": "10.0.1.30",
        "tailscale_service": "active",
        "tailscale_backend": "Running",
        "tailscale_ip": "100.64.0.10",
    }
    base.update(overrides)
    proc = subprocess.run(
        ["python3", str(CLASSIFIER)],
        input=json.dumps(base),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


assert CLASSIFIER.is_file(), f"missing classifier: {CLASSIFIER}"

healthy = classify()
assert healthy["schema"] == "cyberhive.health.classes.v1", healthy
assert healthy["local_safe"] == "pass", healthy
assert healthy["connected"] == "pass", healthy
assert healthy["remote_ready"] == "pass", healthy
assert healthy["reasons"]["local_safe"] == [], healthy
assert healthy["reasons"]["connected"] == [], healthy
assert healthy["reasons"]["remote_ready"] == [], healthy

offline = classify(lan_ip="", tailscale_service="inactive", tailscale_backend="Stopped", tailscale_ip="")
assert offline["local_safe"] == "pass", offline
assert offline["connected"] == "fail", offline
assert offline["remote_ready"] == "fail", offline
assert offline["reasons"]["local_safe"] == [], offline
assert offline["reasons"]["connected"] == ["no-local-network"], offline
assert offline["reasons"]["remote_ready"] == [
    "tailscaled-inactive",
    "tailscale-backend-not-running",
    "tailscale-ip-missing",
], offline

tailscale_outage = classify(tailscale_backend="Stopped", tailscale_ip="")
assert tailscale_outage["local_safe"] == "pass", tailscale_outage
assert tailscale_outage["connected"] == "pass", tailscale_outage
assert tailscale_outage["remote_ready"] == "fail", tailscale_outage

web_down = classify(web_service="failed")
assert web_down["local_safe"] == "fail", web_down
assert web_down["reasons"]["local_safe"] == ["web-inactive"], web_down

state_missing = classify(persistence_state="unavailable")
assert state_missing["local_safe"] == "fail", state_missing
assert state_missing["reasons"]["local_safe"] == ["persistence-unavailable"], state_missing

guard_fail = classify(host_disk_guard="fail")
assert guard_fail["local_safe"] == "fail", guard_fail
assert guard_fail["reasons"]["local_safe"] == ["host-disk-guard"], guard_fail

multiple = classify(
    onboarding_service="failed",
    ssh_service="inactive",
    web_service="failed",
    mdns_service="inactive",
    host_disk_guard="fail",
    persistence_state="unavailable",
)
assert multiple["reasons"]["local_safe"] == [
    "onboarding-inactive",
    "ssh-inactive",
    "web-inactive",
    "mdns-inactive",
    "host-disk-guard",
    "persistence-unavailable",
], multiple

nonpersistent = classify(persistence="ephemeral", persistence_state="unknown")
assert nonpersistent["local_safe"] == "pass", nonpersistent

print("CyberHIVE deterministic health classifier behavior passed")
