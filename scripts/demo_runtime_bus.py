#!/usr/bin/env python3
"""Run a tiny CyberHIVE Runtime Bus demo."""
from __future__ import annotations

import tempfile
from pathlib import Path

from cyberhive_core import AppendOnlyLog, Operation, OperationType, RuntimeBus, StateEngine
from cyberhive_core.data_fabric import DataObject, PlacementEngine


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        log = AppendOnlyLog(Path(tmp) / "runtime.jsonl")
        state = StateEngine()
        bus = RuntimeBus(node_id="local-demo", log_store=log, state_engine=state, max_ops=3)

        bus.publish(Operation.from_json_payload(OperationType.SET, "nodes.local.gpu", {"name": "RTX 3070"}))
        bus.publish(Operation.from_json_payload(OperationType.PATCH, "nodes.local.gpu", {"temp_c": 67}))
        bus.publish(Operation.from_json_payload(OperationType.OBSERVE, "telemetry.gpu", {"temp_c": 67}))
        bus.flush()

        placement = PlacementEngine().decide(
            DataObject(
                id="model.llama.local",
                size_bytes=7_000_000_000,
                reads_1h=90,
                reads_24h=700,
                latency_requirement="high",
                exclusivity="high_fanout",
                predicted_use=0.8,
                reconstruction_seconds=7200,
            )
        )

        print("frames:", log.count())
        print("revision:", state.revision)
        print("state:", state.snapshot()["state"])
        print("placement:", placement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
