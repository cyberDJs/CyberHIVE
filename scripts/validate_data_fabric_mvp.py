#!/usr/bin/env python3
"""Validate CyberHIVE Adaptive Data Fabric MVP."""
from __future__ import annotations

from cyberhive_core import DataFabric, DataObject, PlacementAction, StorageDevice, StorageTier


def main() -> int:
    fabric = DataFabric()
    fabric.register_device(StorageDevice("ram-a", StorageTier.L1_RAM, "node-a", capacity_bytes=16_000_000_000, used_bytes=2_000_000_000))
    fabric.register_device(StorageDevice("nvme-a", StorageTier.L2_LOCAL_NVME, "node-a", capacity_bytes=1_000_000_000_000, used_bytes=300_000_000_000))
    fabric.register_device(StorageDevice("hdd-a", StorageTier.L4_HDD_RAID, "node-storage", capacity_bytes=8_000_000_000_000, used_bytes=2_000_000_000_000))
    fabric.register_device(StorageDevice("archive-a", StorageTier.L6_ARCHIVE_REMOTE, "node-storage", capacity_bytes=40_000_000_000_000, used_bytes=5_000_000_000_000))

    fabric.register_object(
        DataObject(
            id="model.local.chat",
            size_bytes=7_000_000_000,
            latency_requirement="critical",
            exclusivity="high_fanout",
            predicted_use=0.90,
            reconstruction_seconds=7200,
            current_tier=StorageTier.L4_HDD_RAID,
            preferred_nodes=["node-a"],
        )
    )
    for _ in range(80):
        fabric.record_access("model.local.chat", node_id="node-a")

    hot = fabric.decide("model.local.chat")
    assert hot.tier in {StorageTier.L1_RAM, StorageTier.L2_LOCAL_NVME}, hot
    assert hot.action in {PlacementAction.PROMOTE, PlacementAction.REPLICATE, PlacementAction.MOVE}, hot
    assert hot.replicas >= 2, hot

    fabric.register_object(
        DataObject(
            id="artifact.old.render",
            size_bytes=4_000_000_000,
            latency_requirement="low",
            exclusivity="single_consumer",
            predicted_use=0.0,
            current_tier=StorageTier.L2_LOCAL_NVME,
        )
    )
    cold = fabric.decide("artifact.old.render")
    assert cold.tier in {StorageTier.L4_HDD_RAID, StorageTier.L6_ARCHIVE_REMOTE}, cold
    assert cold.action == PlacementAction.DEMOTE, cold

    fabric.register_object(
        DataObject(
            id="secret.local.cache",
            size_bytes=10_000_000,
            sensitivity="secret",
            current_tier=StorageTier.L6_ARCHIVE_REMOTE,
        )
    )
    secret = fabric.decide("secret.local.cache")
    assert secret.tier == StorageTier.L2_LOCAL_NVME, secret
    assert secret.replicas == 1, secret

    moves = fabric.migration_plan()
    assert any(move.object_id == "model.local.chat" for move in moves), moves
    assert any(move.object_id == "artifact.old.render" and move.action == PlacementAction.DEMOTE for move in moves), moves

    print("OK: Adaptive Data Fabric MVP validation passed")
    print("hot:", hot)
    print("cold:", cold)
    print("secret:", secret)
    print("moves:", len(moves))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
