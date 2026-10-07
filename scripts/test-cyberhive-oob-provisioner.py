#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVISION = ROOT / "scripts/provision-cyberhive-oob-credentials.py"
assert PROVISION.is_file()

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    state = root / "state"
    card = root / "setup-card.json"
    proc = subprocess.run(
        [sys.executable, str(PROVISION), "--state-dir", str(state), "--device-id", "hive-0013", "--setup-card", str(card)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["status"] == "prepared"
    assert result["ssid"] == "CyberHIVE-HIVE0013"
    cred = state / "network/oob-ap.env"
    assert cred.is_file()
    assert card.is_file()
    assert (cred.stat().st_mode & 0o777) == 0o600
    assert (card.stat().st_mode & 0o777) == 0o600
    env = dict(line.split("=", 1) for line in cred.read_text().splitlines())
    payload = json.loads(card.read_text())
    assert payload["ssid"] == env["SSID"]
    assert payload["psk"] == env["PSK"]
    assert payload["setup_url"] == "http://10.42.0.1:8080/"
    assert payload["wifi_qr_payload"].startswith("WIFI:T:WPA;S:CyberHIVE-HIVE0013;P:")
    assert env["PSK"] not in proc.stdout

    second = subprocess.run(
        [sys.executable, str(PROVISION), "--state-dir", str(state), "--device-id", "hive-0013", "--setup-card", str(root / "second.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode != 0
    assert "refusing to overwrite existing credentials" in second.stderr

print("CyberHIVE OOB credential provisioner contract passed")
