#!/usr/bin/env python3
import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CHROOT = ROOT / "infra/live-usb/debian-live/config/includes.chroot"
NETWORK = CHROOT / "usr/local/sbin/cyberhive-oob-network"
ONBOARD = CHROOT / "usr/local/sbin/cyberhive-oob-onboard"
NETWORK_UNIT = CHROOT / "etc/systemd/system/cyberhive-oob-network.service"
ONBOARD_UNIT = CHROOT / "etc/systemd/system/cyberhive-oob-onboard.service"
HOOK = ROOT / "infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot"

for path in (NETWORK, ONBOARD, NETWORK_UNIT, ONBOARD_UNIT):
    assert path.is_file(), path

network = NETWORK.read_text()
onboard = ONBOARD.read_text()
network_unit = NETWORK_UNIT.read_text()
onboard_unit = ONBOARD_UNIT.read_text()
hook = HOOK.read_text()

for marker in (
    "FALLBACK_SECONDS=45",
    "AP_NAME=cyberhive-oob",
    "AP_ADDR=10.42.0.1/24",
    "has_uplink()",
    "wifi_device()",
    "connection.autoconnect no",
    "wifi-sec.key-mgmt wpa-psk",
    "CYBERHIVE_PERSIST_ROOT/state/network/oob-ap.env",
):
    assert marker in network, marker

for marker in (
    'AP_ADDR = "10.42.0.1"',
    'AP_PORT = 8080',
    'CANDIDATE_PREFIX = "cyberhive-oob-candidate-"',
    "def scan()",
    "def connected_l3",
    "def persist_profile",
    "def apply_wifi",
    'self.client_address[0].startswith("10.42.0.")',
    "transaction-active",
    "candidate-not-connected",
):
    assert marker in onboard, marker

assert "ExecStart=/usr/local/sbin/cyberhive-oob-network" in network_unit
assert "ExecStart=/usr/local/sbin/cyberhive-oob-onboard" in onboard_unit
assert "ProtectSystem=strict" in network_unit
assert "ProtectSystem=strict" in onboard_unit
assert "systemctl enable cyberhive-oob-network.service" in hook
assert "systemctl enable cyberhive-oob-onboard.service" in hook
assert "chmod 0755 /usr/local/sbin/cyberhive-oob-network" in hook
assert "chmod 0755 /usr/local/sbin/cyberhive-oob-onboard" in hook

loader = importlib.machinery.SourceFileLoader("cyberhive_oob_onboard", str(ONBOARD))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
loader.exec_module(module)

assert module.apply_wifi("", "secret") == {"status": "rejected", "reason": "invalid-ssid"}
assert module.apply_wifi("x" * 33, "secret") == {"status": "rejected", "reason": "invalid-ssid"}
assert module.apply_wifi("ok", "x" * 129) == {"status": "rejected", "reason": "password-too-long"}

calls = []
def fake_run(*args, timeout=25):
    calls.append(args)
    if args[:3] == ("connection", "delete", "cyberhive-oob-candidate-a665a4592042"):
        return ""
    if args[:3] == ("connection", "down", "cyberhive-oob"):
        return ""
    if args[:3] == ("device", "wifi", "connect"):
        return ""
    return ""

with patch.object(module, "wifi_device", return_value="wlan0"),      patch.object(module, "run", side_effect=fake_run),      patch.object(module, "connected_l3", return_value=True),      patch.object(module, "persist_profile") as persist,      patch.object(module, "write_state"):
    result = module.apply_wifi("123", "secret")

assert result == {"status": "connected", "ssid": "123"}, result
persist.assert_called_once()
connect = next(call for call in calls if call[:3] == ("device", "wifi", "connect"))
assert connect[:7] == ("device", "wifi", "connect", "123", "ifname", "wlan0", "name"), connect
assert "password" in connect and "secret" in connect

with patch.object(module, "wifi_device", return_value="wlan0"),      patch.object(module, "run", return_value=""),      patch.object(module, "connected_l3", return_value=False),      patch.object(module, "persist_profile") as persist,      patch.object(module, "write_state"):
    failed = module.apply_wifi("testnet", "bad")

assert failed["status"] == "failed", failed
persist.assert_not_called()

print("CyberHIVE OOB onboarding contract passed")
