# WB-HIVE-BOOT-0006 preflight evidence — 2026-09-04

Source-of-truth preflight established that PR #28 remained open/draft/not merged at exact head `f1398376d54299c91212c62045f229781d60d45b` before the v0.3 branch was created.

The physically booted v0.2 node was independently reachable from the authorized Mac over Tailscale at `100.95.68.127` using a dedicated SSH public key. Effective SSH configuration was verified as `PubkeyAuthentication yes`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no` before v0.3 implementation began.

Observed target hardware for the remote-development node includes AMD Ryzen 7 5800X, approximately 32 GiB RAM, NVIDIA GeForce RTX 3070, Realtek RTL8822CE Wi-Fi and a protected internal Seagate FireCuda NVMe device. GPU compute enablement is not claimed by this evidence.

This record does not claim a v0.3 image build, USB write, boot, persistence test, OTA test or rollback PASS.
