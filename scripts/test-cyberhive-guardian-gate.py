#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-live-appliance-v0-3.sh"
WORKFLOW = ROOT / ".github/workflows/live-appliance-v0-3.yml"

validator = VALIDATOR.read_text()
workflow = WORKFLOW.read_text()

for required in (
    "infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-guardian",
    "infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-guardian.service",
    "infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-guardian.timer",
    "docs/work-blocks/WB-HIVE-BOOT-0010-guardian-l0-l1.md",
):
    assert required in validator, required

assert "ast.parse" in validator
assert "cyberhive-guardian" in validator
assert "MAX_ATTEMPTS = 3" in validator
assert "CIRCUIT_SECONDS = 900" in validator
assert "runtime Guardian must not reboot, poweroff or mutate GRUB" in validator

for test in (
    "scripts/test-cyberhive-guardian-plan.py",
    "scripts/test-cyberhive-guardian-executor.py",
    "scripts/test-cyberhive-guardian-wiring.py",
    "scripts/test-cyberhive-guardian-state-cycle.py",
    "scripts/test-cyberhive-guardian-gate.py",
):
    assert test in workflow, test
    assert f"python3 {test}" in workflow, test

print("CyberHIVE Guardian CI/validator gate wiring passed")
