#!/usr/bin/env python3
"""Demo: behavior-driven data placement without cloud billing logic."""
from __future__ import annotations

from cyberhive_core import DataFabric, DataObject, StorageDevice, StorageTier


def main() -> int:
    fabric = DataFabric()
    fabric.register_device(StorageDevice("ram-main", StorageTier.L1_RAM, "hive-a", 32_000_000_000, 8_000_000_000))
    fabric.register_device(StorageDevice("nvme-main", StorageTier.L2_LOCAL_NVME, "hive-a", 2_000_000_000_000, 600_000_000_000))
    fabric.register_device(StorageDevice("hdd-raid", StorageTier.L4_HDD_RAID, "hive-storage", 12_000_000_000_000, 3_000_000_000_000))
    fabric.register_device(StorageDevice("archive", StorageTier.L6_ARCHIVE_REMOTE, "hive-storage", 40_000_000_000_000, 4_000_000_000_000))

    fabric.register_object(
        DataObject(
            id="dataset.session.current",
            size_bytes=1_200_000_000,
            current_tier=StorageTier.L4_HDD_RAID,
            latency_requirement="high",
            predicted_use=0.7,
            reconstruction_seconds=3600,
            preferred_nodes=["hive-a"],
        )
    )
    fabric.register_object(
        DataObject(
            id="video.archive.raw-2026-08-01",
            size_bytes=24_000_000_000,
            current_tier=StorageTier.L2_LOCAL_NVME,
            latency_requirement="low",
            predicted_use=0.0,
        )
    )

    for _ in range(30):
        fabric.record_access("dataset.session.current", node_id="hive-a")

    for move in fabric.migration_plan():
        print(f"{move.action.value}: {move.object_id} -> {move.to_tier.value} replicas={move.replicas} targets={list(move.target_devices)}")
        print(f"  {move.reason}")

    print("tier usage:", fabric.tier_usage())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
