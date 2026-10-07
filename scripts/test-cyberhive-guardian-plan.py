#!/usr/bin/env python3
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDIAN = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-guardian"

assert GUARDIAN.is_file(), f"missing guardian: {GUARDIAN}"
loader = SourceFileLoader("cyberhive_guardian", str(GUARDIAN))
spec = importlib.util.spec_from_loader("cyberhive_guardian", loader)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def health(local="pass", connected="pass", remote="pass", *, local_reasons=None, connected_reasons=None, remote_reasons=None):
    return {
        "health": {
            "local_safe": local,
            "connected": connected,
            "remote_ready": remote,
            "reasons": {
                "local_safe": list(local_reasons or []),
                "connected": list(connected_reasons or []),
                "remote_ready": list(remote_reasons or []),
            },
        }
    }


def plan(h, state=None, now=1000):
    return mod.plan_repair(h, state or {"schema": "cyberhive.guardian.state.v1", "actions": {}}, now)


idle = plan(health())
assert idle["action"] is None, idle
assert idle["reason"] == "healthy", idle

web = plan(health(local="fail", local_reasons=["web-inactive"]))
assert web["action"] == "restart-web", web
assert web["level"] == "L0", web

ssh = plan(health(local="fail", local_reasons=["ssh-inactive"]))
assert ssh["action"] == "restart-ssh", ssh
assert ssh["level"] == "L0", ssh

mdns = plan(health(local="fail", local_reasons=["mdns-inactive"]))
assert mdns["action"] == "restart-mdns", mdns
assert mdns["level"] == "L0", mdns

net = plan(health(connected="fail", remote="fail", connected_reasons=["no-local-network"], remote_reasons=["tailscale-backend-not-running", "tailscale-ip-missing"]))
assert net["action"] == "reconnect-network", net
assert net["level"] == "L1", net

tailscaled = plan(health(remote="fail", remote_reasons=["tailscaled-inactive", "tailscale-backend-not-running", "tailscale-ip-missing"]))
assert tailscaled["action"] == "restart-tailscaled", tailscaled
assert tailscaled["level"] == "L0", tailscaled

tail_backend = plan(health(remote="fail", remote_reasons=["tailscale-backend-not-running", "tailscale-ip-missing"]))
assert tail_backend["action"] == "restart-tailscaled", tail_backend
assert tail_backend["level"] == "L1", tail_backend

for reason in ("host-disk-guard", "persistence-unavailable", "onboarding-inactive"):
    blocked = plan(health(local="fail", local_reasons=[reason]))
    assert blocked["action"] is None, blocked
    assert blocked["reason"] == "manual-required", blocked

# Only one repair is selected per run and local safety repairs take priority.
priority = plan(
    health(
        local="fail",
        connected="fail",
        remote="fail",
        local_reasons=["web-inactive", "mdns-inactive"],
        connected_reasons=["no-local-network"],
        remote_reasons=["tailscaled-inactive"],
    )
)
assert priority["action"] == "restart-web", priority

# Bounded retry contract: 3 attempts / 10 minute window, >=60s spacing,
# then a 15 minute circuit breaker.
first = plan(health(local="fail", local_reasons=["web-inactive"]), now=1000)
state = first["state"]
assert first["action"] == "restart-web", first
assert state["actions"]["restart-web"]["attempts"] == 1, state

cooldown = plan(health(local="fail", local_reasons=["web-inactive"]), state=state, now=1030)
assert cooldown["action"] is None and cooldown["reason"] == "cooldown", cooldown

second = plan(health(local="fail", local_reasons=["web-inactive"]), state=cooldown["state"], now=1061)
state = second["state"]
assert second["action"] == "restart-web", second
assert state["actions"]["restart-web"]["attempts"] == 2, state

third = plan(health(local="fail", local_reasons=["web-inactive"]), state=state, now=1122)
state = third["state"]
assert third["action"] == "restart-web", third
assert state["actions"]["restart-web"]["attempts"] == 3, state

opened = plan(health(local="fail", local_reasons=["web-inactive"]), state=state, now=1183)
assert opened["action"] is None and opened["reason"] == "circuit-open", opened
assert opened["state"]["actions"]["restart-web"]["circuit_until"] == 2083, opened

still_open = plan(health(local="fail", local_reasons=["web-inactive"]), state=opened["state"], now=1500)
assert still_open["action"] is None and still_open["reason"] == "circuit-open", still_open

recovered = plan(health(local="fail", local_reasons=["web-inactive"]), state=still_open["state"], now=2090)
assert recovered["action"] == "restart-web", recovered
assert recovered["state"]["actions"]["restart-web"]["attempts"] == 1, recovered

print("CyberHIVE Guardian deterministic L0/L1 planner behavior passed")
