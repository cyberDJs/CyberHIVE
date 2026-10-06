#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHROOT = ROOT / "infra/live-usb/debian-live/config/includes.chroot"
ATTEST = CHROOT / "usr/local/bin/cyberhive-management-firewall-attest"
LIVE = CHROOT / "usr/local/bin/cyberhive-live-health"
SUDOERS = CHROOT / "etc/sudoers.d/91-cyberhive-firewall-attest"
HOOK = ROOT / "infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot"
WEB_SERVICE = CHROOT / "etc/systemd/system/cyberhive-web.service"

attest = ATTEST.read_text()
live = LIVE.read_text()

assert attest.startswith("#!/usr/bin/python3\n"), "attestor must use fixed interpreter"
assert "len(sys.argv) != 1" in attest
assert SUDOERS.is_file(), f"missing sudoers capability: {SUDOERS}"

sudoers = SUDOERS.read_text()
hook = HOOK.read_text()
web_service = WEB_SERVICE.read_text()
assert "chmod 0440 /etc/sudoers.d/91-cyberhive-firewall-attest" in hook
assert "User=cyberhive-web" in web_service
assert "cyberhive ALL=(root) NOPASSWD: /usr/local/bin/cyberhive-management-firewall-attest" in sudoers
assert "cyberhive-web ALL=(root) NOPASSWD: /usr/local/bin/cyberhive-management-firewall-attest" in sudoers
assert "/usr/local/bin/cyberhive-management-firewall-attest" in sudoers
assert "cyberhive-management-firewall " not in sudoers
assert "iptables" not in sudoers
assert "ip6tables" not in sudoers

assert 'if [ "$(id -u)" -eq 0 ]; then' in live
assert "/usr/local/bin/cyberhive-management-firewall-attest" in live
assert "sudo -n /usr/local/bin/cyberhive-management-firewall-attest" in live

print("CyberHIVE firewall attestation least-privilege execution contract passed")
