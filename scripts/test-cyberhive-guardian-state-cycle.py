#!/usr/bin/env python3
import importlib.util
import json
import stat
import subprocess
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDIAN = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-guardian"

loader = SourceFileLoader("cyberhive_guardian", str(GUARDIAN))
spec = importlib.util.spec_from_loader("cyberhive_guardian", loader)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

assert hasattr(mod, "run_cycle"), "Guardian run_cycle missing"


class FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(tuple(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


def web_down():
    return {
        "health": {
            "local_safe": "fail",
            "connected": "pass",
            "remote_ready": "pass",
            "reasons": {
                "local_safe": ["web-inactive"],
                "connected": [],
                "remote_ready": [],
            },
        }
    }


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    state = root / "persist/state/guardian/state.json"
    evidence = root / "run/evidence/guardian.json"

    fake = FakeRunner()
    first = mod.run_cycle(
        web_down(),
        state_path=state,
        evidence_path=evidence,
        persisted=True,
        now=1000,
        runner=fake,
    )
    assert first["plan"]["action"] == "restart-web", first
    assert first["result"]["status"] == "executed", first
    assert state.is_file(), state
    assert evidence.is_file(), evidence

    state_json = json.loads(state.read_text())
    assert state_json["actions"]["restart-web"]["attempts"] == 1, state_json
    evidence_json = json.loads(evidence.read_text())
    assert evidence_json == first, (evidence_json, first)
    assert stat.S_IMODE(state.stat().st_mode) == 0o600
    assert stat.S_IMODE(evidence.stat().st_mode) == 0o640

    before_calls = len(fake.calls)
    cooldown = mod.run_cycle(
        web_down(),
        state_path=state,
        evidence_path=evidence,
        persisted=True,
        now=1030,
        runner=fake,
    )
    assert cooldown["plan"]["action"] is None, cooldown
    assert cooldown["plan"]["reason"] == "cooldown", cooldown
    assert cooldown["result"]["status"] == "idle", cooldown
    assert len(fake.calls) == before_calls, fake.calls

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    state = root / "persist/state/guardian/state.json"
    evidence = root / "run/evidence/guardian.json"
    fake = FakeRunner()

    blocked = mod.run_cycle(
        web_down(),
        state_path=state,
        evidence_path=evidence,
        persisted=False,
        now=2000,
        runner=fake,
    )
    assert blocked["plan"]["action"] == "restart-web", blocked
    assert blocked["result"] == {
        "status": "blocked",
        "reason": "persistence-unavailable",
    }, blocked
    assert not state.exists(), state
    assert evidence.is_file(), evidence
    assert fake.calls == [], fake.calls


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    state = root / "persist/state/guardian/state.json"
    evidence = root / "run/evidence/guardian.json"
    state.parent.mkdir(parents=True)
    state.write_text("{broken-json", encoding="utf-8")
    fake = FakeRunner()

    invalid = mod.run_cycle(
        web_down(),
        state_path=state,
        evidence_path=evidence,
        persisted=True,
        now=3000,
        runner=fake,
    )
    assert invalid["plan"]["action"] is None, invalid
    assert invalid["plan"]["reason"] == "guardian-state-invalid", invalid
    assert invalid["result"] == {
        "status": "blocked",
        "reason": "guardian-state-invalid",
    }, invalid
    assert state.read_text(encoding="utf-8") == "{broken-json"
    assert fake.calls == [], fake.calls

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    state = root / "persist/state/guardian/state.json"
    evidence = root / "run/evidence/guardian.json"
    state.parent.mkdir(parents=True)
    type_corrupt_state = {
        "schema": mod.SCHEMA,
        "actions": {
            "restart-web": {
                "window_start": 1000,
                "attempts": "not-an-int",
                "last_attempt": 1000,
                "circuit_until": 0,
            }
        },
    }
    original = json.dumps(type_corrupt_state, sort_keys=True, separators=(",", ":")) + "\n"
    state.write_text(original, encoding="utf-8")
    fake = FakeRunner()

    invalid = mod.run_cycle(
        web_down(),
        state_path=state,
        evidence_path=evidence,
        persisted=True,
        now=4000,
        runner=fake,
    )
    assert invalid["plan"]["action"] is None, invalid
    assert invalid["plan"]["reason"] == "guardian-state-invalid", invalid
    assert invalid["result"] == {
        "status": "blocked",
        "reason": "guardian-state-invalid",
    }, invalid
    assert state.read_text(encoding="utf-8") == original
    assert evidence.is_file(), evidence
    assert fake.calls == [], fake.calls

print("CyberHIVE Guardian persistent retry/evidence cycle passed")
