#!/usr/bin/env python3
"""Validate Runtime Bus MVP without third-party dependencies."""
from __future__ import annotations

import tempfile
from pathlib import Path

from cyberhive_core import AppendOnlyLog, CacheFabric, CachePolicy, Operation, OperationType, RuntimeBus, StateEngine
from cyberhive_core.data_fabric import DataObject, PlacementEngine, StorageTier


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        log = AppendOnlyLog(Path(tmp) / "runtime.jsonl")
        state = StateEngine()
        bus = RuntimeBus(node_id="validator", log_store=log, state_engine=state, max_ops=2)
        bus.publish(Operation.from_json_payload(OperationType.SET, "nodes.alpha", {"status": "online"}))
        bus.publish(Operation.from_json_payload(OperationType.PATCH, "nodes.alpha", {"gpu": "RTX 3070"}))
        bus.publish(Operation.from_json_payload(OperationType.OBSERVE, "telemetry.alpha", {"load": 0.42}))
        bus.flush()
        assert log.count() == 2, log.count()
        assert state.state["nodes"]["alpha"]["gpu"] == "RTX 3070"
        assert state.revision == 3

        cache = CacheFabric()
        key = cache.make_key(operation="inventory.read", normalized_input={"node": "alpha"}, relevant_state=state.revision)
        cache.put(key, {"status": "online"}, policy=CachePolicy(ttl_seconds=60))
        assert cache.get(key) == {"status": "online"}
        assert cache.stats()["hits"] == 1

        decision = PlacementEngine().decide(
            DataObject(
                id="hot-artifact",
                size_bytes=1_000_000,
                reads_1h=120,
                reads_24h=900,
                latency_requirement="critical",
                exclusivity="high_fanout",
                predicted_use=1.0,
                reconstruction_seconds=3600,
            )
        )
        assert decision.tier in {StorageTier.L1_RAM, StorageTier.L2_LOCAL_NVME}
    print("OK: Runtime Bus MVP validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
