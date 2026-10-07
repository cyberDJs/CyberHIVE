#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"

def generate_credentials(device_id: str) -> dict[str, str]:
    clean = "".join(ch for ch in device_id.upper() if ch.isalnum())[-8:] or secrets.token_hex(4).upper()
    psk = "".join(secrets.choice(ALPHABET) for _ in range(20))
    return {
        "schema": "cyberhive.oob.credentials.v1",
        "ssid": f"CyberHIVE-{clean}",
        "psk": psk,
    }

def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare per-device CyberHIVE OOB credentials in an explicitly supplied STATE directory."
    )
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--setup-card", required=True, type=Path)
    args = parser.parse_args()

    state_dir = args.state_dir.resolve()
    credential_path = state_dir / "network" / "oob-ap.env"
    if credential_path.exists():
        raise SystemExit(f"refusing to overwrite existing credentials: {credential_path}")
    if args.setup_card.exists():
        raise SystemExit(f"refusing to overwrite existing setup card: {args.setup_card}")

    creds = generate_credentials(args.device_id)
    env = f"SSID={creds['ssid']}\nPSK={creds['psk']}\n"
    write_private(credential_path, env)

    card = {
        **creds,
        "setup_url": "http://10.42.0.1:8080/",
        "wifi_qr_payload": f"WIFI:T:WPA;S:{creds['ssid']};P:{creds['psk']};;",
    }
    write_private(args.setup_card.resolve(), json.dumps(card, indent=2) + "\n")
    print(json.dumps({"status": "prepared", "ssid": creds["ssid"], "setup_card": str(args.setup_card)}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
