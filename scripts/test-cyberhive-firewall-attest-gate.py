#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-live-appliance-v0-3.sh"
WORKFLOW = ROOT / ".github/workflows/live-appliance-v0-3.yml"

validator = VALIDATOR.read_text()
workflow = WORKFLOW.read_text()

for required in (
    "infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-management-firewall-attest",
    "infra/live-usb/debian-live/config/includes.chroot/etc/sudoers.d/91-cyberhive-firewall-attest",
    "docs/work-blocks/WB-HIVE-BOOT-0011-firewall-attestation.md",
):
    assert required in validator, required

for marker in (
    "cyberhive.management.firewall.attestation.v1",
    "ipv4-prefix-mismatch",
    "ipv6-prefix-mismatch",
    "management_firewall",
    "management-firewall-unattested",
    "sudo -n /usr/local/bin/cyberhive-management-firewall-attest",
):
    assert marker in validator, marker

for test in (
    "scripts/test-cyberhive-firewall-attest.py",
    "scripts/test-cyberhive-firewall-health-contract.py",
    "scripts/test-cyberhive-firewall-attest-privilege.py",
    "scripts/test-cyberhive-firewall-attest-gate.py",
):
    assert test in workflow, test
    assert f"python3 {test}" in workflow, test

print("CyberHIVE firewall attestation CI/validator gate wiring passed")
