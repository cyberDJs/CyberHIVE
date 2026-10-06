#!/usr/bin/env python3
import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATTEST = ROOT / "infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-management-firewall-attest"

assert ATTEST.is_file(), f"missing firewall attestor: {ATTEST}"
loader = SourceFileLoader("cyberhive_firewall_attest", str(ATTEST))
spec = importlib.util.spec_from_loader("cyberhive_firewall_attest", loader)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

V4 = """-A INPUT ! -i tailscale0 -s 169.254.0.0/16 -p tcp -m tcp --dport 80 -j ACCEPT
-A INPUT ! -i tailscale0 -s 192.168.0.0/16 -p tcp -m tcp --dport 80 -j ACCEPT
-A INPUT ! -i tailscale0 -s 172.16.0.0/12 -p tcp -m tcp --dport 80 -j ACCEPT
-A INPUT ! -i tailscale0 -s 10.0.0.0/8 -p tcp -m tcp --dport 80 -j ACCEPT
-A INPUT ! -i tailscale0 -s 127.0.0.0/8 -p tcp -m tcp --dport 80 -j ACCEPT
-A INPUT ! -i tailscale0 -p tcp -m tcp --dport 80 -j DROP
-A INPUT ! -i tailscale0 -p tcp -m tcp --dport 22 -j DROP
-A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
"""

V6 = """-A INPUT ! -i tailscale0 -s fe80::/10 -p tcp -m tcp --dport 80 -j ACCEPT
-A INPUT ! -i tailscale0 -s fc00::/7 -p tcp -m tcp --dport 80 -j ACCEPT
-A INPUT ! -i tailscale0 -s ::1/128 -p tcp -m tcp --dport 80 -j ACCEPT
-A INPUT ! -i tailscale0 -p tcp -m tcp --dport 80 -j DROP
-A INPUT ! -i tailscale0 -p tcp -m tcp --dport 22 -j DROP
"""

good = mod.attest_rule_lines(V4.splitlines(), V6.splitlines())
assert good["status"] == "pass", good
assert good["ipv4"] == "pass", good
assert good["ipv6"] == "pass", good
assert good["reasons"] == [], good

# A broad rule above the CyberHIVE prefix can bypass the intended DROP rules.
bypass = mod.attest_rule_lines(
    ["-A INPUT -j ACCEPT", *V4.splitlines()],
    V6.splitlines(),
)
assert bypass["status"] == "fail", bypass
assert "ipv4-prefix-mismatch" in bypass["reasons"], bypass

# Merely keeping most rules is insufficient if an SSH DROP disappeared.
missing_ssh = mod.attest_rule_lines(
    [line for line in V4.splitlines() if "--dport 22" not in line],
    V6.splitlines(),
)
assert missing_ssh["status"] == "fail", missing_ssh
assert "ipv4-prefix-mismatch" in missing_ssh["reasons"], missing_ssh

wrong_v6 = mod.attest_rule_lines(
    V4.splitlines(),
    ["-A INPUT -j ACCEPT", *V6.splitlines()],
)
assert wrong_v6["status"] == "fail", wrong_v6
assert "ipv6-prefix-mismatch" in wrong_v6["reasons"], wrong_v6

# iptables -S may render an explicit all-source CIDR; normalize it.
v4_explicit_all = V4.replace(
    "-A INPUT ! -i tailscale0 -p tcp -m tcp --dport 22 -j DROP",
    "-A INPUT ! -i tailscale0 -s 0.0.0.0/0 -p tcp -m tcp --dport 22 -j DROP",
)
normalized = mod.attest_rule_lines(v4_explicit_all.splitlines(), V6.splitlines())
assert normalized["status"] == "pass", normalized

print("CyberHIVE management firewall semantic prefix attestation passed")
