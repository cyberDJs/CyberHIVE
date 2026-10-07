#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

REPO = Path(__file__).resolve().parents[1]
LIVE_ROOT = REPO / "infra/live-usb/debian-live"
DEFAULTS = (
    LIVE_ROOT
    / "config/includes.chroot/etc/live/config.conf.d/10-cyberhive-identity.conf"
)
AUTO_CONFIG = LIVE_ROOT / "auto/config"
DISK_BUILDER = LIVE_ROOT / "build-unattended-disk-image.sh"


class LiveIdentityFallbackTest(unittest.TestCase):
    def test_live_config_defaults_pin_identity_without_kernel_parameters(self) -> None:
        self.assertTrue(
            DEFAULTS.is_file(),
            f"missing live-config fallback {DEFAULTS.relative_to(REPO)}",
        )

        result = subprocess.run(
            [
                "sh",
                "-c",
                (
                    'LIVE_USERNAME=user; LIVE_HOSTNAME=debian; '
                    '. "$1"; '
                    'printf "%s\\n%s\\n" "$LIVE_USERNAME" "$LIVE_HOSTNAME"'
                ),
                "sh",
                str(DEFAULTS),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.stdout.splitlines(),
            ["cyberhive", "cyberhive-live"],
        )

    def test_boot_cmdlines_keep_identity_as_defense_in_depth(self) -> None:
        auto_text = AUTO_CONFIG.read_text(encoding="utf-8")
        builder_text = DISK_BUILDER.read_text(encoding="utf-8")

        for text in (auto_text, builder_text):
            self.assertIn("username=cyberhive", text)
            self.assertIn("hostname=cyberhive-live", text)


if __name__ == "__main__":
    unittest.main()
