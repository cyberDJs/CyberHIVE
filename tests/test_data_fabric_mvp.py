import unittest

from cyberhive_core import DataFabric, DataObject, PlacementAction, PlacementEngine, StorageDevice, StorageTier


class DataFabricMvpTests(unittest.TestCase):
    def test_patch_002_placement_api_still_works(self):
        decision = PlacementEngine().decide(
            DataObject(
                id="hot-artifact",
                size_bytes=10,
                reads_1h=120,
                reads_24h=900,
                latency_requirement="critical",
                exclusivity="high_fanout",
                predicted_use=1.0,
                reconstruction_seconds=3600,
            )
        )
        self.assertIn(decision.tier, {StorageTier.L1_RAM, StorageTier.L2_LOCAL_NVME})
        self.assertGreaterEqual(decision.replicas, 2)

    def test_access_observations_change_placement(self):
        fabric = DataFabric()
        fabric.register_device(StorageDevice("ram", StorageTier.L1_RAM, "node-a", 10_000_000_000, 1_000_000_000))
        fabric.register_object(
            DataObject(
                id="active.dataset",
                size_bytes=10_000_000,
                current_tier=StorageTier.L4_HDD_RAID,
                latency_requirement="high",
                predicted_use=0.7,
            )
        )
        for _ in range(100):
            fabric.record_access("active.dataset", node_id="node-a")
        decision = fabric.decide("active.dataset")
        self.assertIn(decision.action, {PlacementAction.PROMOTE, PlacementAction.MOVE})
        self.assertEqual(decision.target_devices, ("ram",))

    def test_cold_object_demotes(self):
        fabric = DataFabric()
        fabric.register_object(
            DataObject(
                id="cold.render",
                size_bytes=10_000_000,
                current_tier=StorageTier.L2_LOCAL_NVME,
                latency_requirement="low",
                predicted_use=0.0,
            )
        )
        decision = fabric.decide("cold.render")
        self.assertEqual(decision.action, PlacementAction.DEMOTE)
        self.assertIn(decision.tier, {StorageTier.L4_HDD_RAID, StorageTier.L6_ARCHIVE_REMOTE})

    def test_secret_data_stays_local_fast_and_single_replica(self):
        decision = PlacementEngine().decide(DataObject(id="secret", size_bytes=1, sensitivity="secret", reads_24h=9999))
        self.assertEqual(decision.tier, StorageTier.L2_LOCAL_NVME)
        self.assertEqual(decision.replicas, 1)


if __name__ == "__main__":
    unittest.main()
