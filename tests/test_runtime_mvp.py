#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cyberhive_core import AppendOnlyLog, CacheFabric, CachePolicy, Operation, OperationType, RuntimeBus, StateEngine
from cyberhive_core.data_fabric import DataObject, PlacementEngine, StorageTier


class RuntimeMvpTest(unittest.TestCase):
    def test_microbatch_log_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = AppendOnlyLog(Path(tmp) / "runtime.jsonl")
            state = StateEngine()
            bus = RuntimeBus(node_id="test", log_store=log, state_engine=state, max_ops=2)
            bus.publish(Operation.from_json_payload(OperationType.SET, "nodes.alpha", {"status": "online"}))
            bus.publish(Operation.from_json_payload(OperationType.PATCH, "nodes.alpha", {"gpu": "RTX 3070"}))
            bus.publish(Operation.from_json_payload(OperationType.OBSERVE, "telemetry.alpha", {"load": 0.42}))
            bus.flush()
            self.assertEqual(log.count(), 2)
            self.assertEqual(state.state["nodes"]["alpha"]["gpu"], "RTX 3070")
            self.assertEqual(state.revision, 3)

    def test_cache_refuses_secret_by_default(self) -> None:
        cache = CacheFabric()
        key = cache.make_key(operation="x", normalized_input={"a": 1})
        with self.assertRaises(ValueError):
            cache.put(key, "secret", policy=CachePolicy(sensitivity="secret"))

    def test_placement_prefers_fast_tier_for_hot_data(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
