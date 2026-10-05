#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "infra/live-usb/debian-live/config/includes.chroot"
WRAPPER = ROOT / "usr/local/sbin/cyberhive-tty1-getty"
DROPIN = ROOT / "etc/systemd/system/getty@tty1.service.d/20-cyberhive-firstboot-autologin.conf"


class FirstbootTty1AutologinTest(unittest.TestCase):
    def test_getty_dropin_orders_persistence_and_uses_guarded_wrapper(self) -> None:
        self.assertTrue(DROPIN.is_file(), f"missing {DROPIN.relative_to(REPO)}")
        text = DROPIN.read_text(encoding="utf-8")
        self.assertIn("Wants=cyberhive-persist-init.service", text)
        self.assertIn("After=cyberhive-persist-init.service", text)
        self.assertIn("ExecStart=\n", text)
        self.assertIn("ExecStart=-/usr/local/sbin/cyberhive-tty1-getty %I $TERM", text)

    def test_wrapper_autologins_only_before_provisioning(self) -> None:
        self.assertTrue(WRAPPER.is_file(), f"missing {WRAPPER.relative_to(REPO)}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            persist = tmp_path / "persist"
            (persist / "state").mkdir(parents=True)
            config = tmp_path / "config.env"
            config.write_text(f'CYBERHIVE_PERSIST_ROOT="{persist}"\n', encoding="utf-8")
            capture = tmp_path / "argv.txt"
            fake_agetty = tmp_path / "agetty"
            fake_agetty.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$@\" >\"$CYBERHIVE_AGETTY_CAPTURE\"\n",
                encoding="utf-8",
            )
            fake_agetty.chmod(0o755)
            env = os.environ.copy()
            env.update(
                CYBERHIVE_CONFIG_ENV=str(config),
                CYBERHIVE_AGETTY_BIN=str(fake_agetty),
                CYBERHIVE_AGETTY_CAPTURE=str(capture),
            )

            subprocess.run([str(WRAPPER), "tty1", "linux"], env=env, check=True)
            self.assertEqual(
                capture.read_text(encoding="utf-8").splitlines(),
                ["--autologin", "cyberhive", "--noclear", "tty1", "linux"],
            )

            (persist / "state/provisioned").write_text("ok\n", encoding="utf-8")
            subprocess.run([str(WRAPPER), "tty1", "linux"], env=env, check=True)
            self.assertEqual(
                capture.read_text(encoding="utf-8").splitlines(),
                ["--noclear", "tty1", "linux"],
            )


if __name__ == "__main__":
    unittest.main()
