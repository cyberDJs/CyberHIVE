#!/usr/bin/env python3
import importlib.util
from importlib.machinery import SourceFileLoader
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDIAN = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-guardian"

assert GUARDIAN.is_file(), f"missing guardian: {GUARDIAN}"
loader = SourceFileLoader("cyberhive_guardian", str(GUARDIAN))
spec = importlib.util.spec_from_loader("cyberhive_guardian", loader)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeRunner:
    def __init__(self, *, firewall_ok=True, sshd_ok=True, nm_active=True, devices="eth0:ethernet:disconnected\nwlan0:wifi:disconnected\n"):
        self.firewall_ok = firewall_ok
        self.sshd_ok = sshd_ok
        self.nm_active = nm_active
        self.devices = devices
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(tuple(argv))
        rc = 0
        stdout = ""
        if argv[:3] == ["systemctl", "is-active", "--quiet"] and argv[3] == "cyberhive-management-firewall.service":
            rc = 0 if self.firewall_ok else 3
        elif argv == ["/usr/sbin/sshd", "-t"]:
            rc = 0 if self.sshd_ok else 1
        elif argv[:3] == ["systemctl", "is-active", "--quiet"] and argv[3] == "NetworkManager.service":
            rc = 0 if self.nm_active else 3
        elif argv == ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
            stdout = self.devices
        return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr="")


def ran(fake, *argv):
    return tuple(argv) in fake.calls


fake = FakeRunner()
result = mod.execute_action("restart-web", fake)
assert result["status"] == "executed", result
assert ran(fake, "cyberhive-host-disk-guard"), fake.calls
assert ran(fake, "systemctl", "is-active", "--quiet", "cyberhive-management-firewall.service"), fake.calls
assert ran(fake, "systemctl", "restart", "cyberhive-web.service"), fake.calls

fake = FakeRunner()
result = mod.execute_action("restart-ssh", fake)
assert result["status"] == "executed", result
assert ran(fake, "/usr/sbin/sshd", "-t"), fake.calls
assert ran(fake, "systemctl", "restart", "ssh.service"), fake.calls

fake = FakeRunner(sshd_ok=False)
result = mod.execute_action("restart-ssh", fake)
assert result["status"] == "blocked", result
assert result["reason"] == "sshd-config-invalid", result
assert not ran(fake, "systemctl", "restart", "ssh.service"), fake.calls

for action, forbidden in (
    ("restart-web", ("systemctl", "restart", "cyberhive-web.service")),
    ("restart-ssh", ("systemctl", "restart", "ssh.service")),
    ("restart-mdns", ("systemctl", "restart", "avahi-daemon.service")),
    ("restart-tailscaled", ("systemctl", "restart", "tailscaled.service")),
    ("reconnect-network", ("nmcli", "connection", "reload")),
):
    fake = FakeRunner(firewall_ok=False)
    result = mod.execute_action(action, fake)
    assert result["status"] == "blocked", (action, result)
    assert result["reason"] == "management-firewall-inactive", (action, result)
    assert tuple(forbidden) not in fake.calls, (action, fake.calls)

fake = FakeRunner()
result = mod.execute_action("restart-mdns", fake)
assert result["status"] == "executed", result
assert ran(fake, "systemctl", "restart", "avahi-daemon.service"), fake.calls

fake = FakeRunner()
result = mod.execute_action("restart-tailscaled", fake)
assert result["status"] == "executed", result
assert ran(fake, "systemctl", "restart", "tailscaled.service"), fake.calls

fake = FakeRunner(nm_active=False)
result = mod.execute_action("reconnect-network", fake)
assert result["status"] == "executed", result
assert ran(fake, "systemctl", "restart", "NetworkManager.service"), fake.calls
assert ran(fake, "nmcli", "connection", "reload"), fake.calls
assert ran(fake, "nmcli", "networking", "on"), fake.calls
assert ran(fake, "nmcli", "radio", "wifi", "on"), fake.calls
assert ran(fake, "nmcli", "--wait", "10", "device", "connect", "eth0"), fake.calls
assert ran(fake, "nmcli", "--wait", "10", "device", "connect", "wlan0"), fake.calls

fake = FakeRunner()
result = mod.execute_action("definitely-not-allowed", fake)
assert result["status"] == "blocked", result
assert result["reason"] == "unknown-action", result

for call in fake.calls:
    assert "reboot" not in call
    assert "grub-editenv" not in call

print("CyberHIVE Guardian executor allowlist and security preconditions passed")
