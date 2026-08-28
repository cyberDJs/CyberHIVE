#!/usr/bin/env python3
from cyberhive_core.scheduler_router import ComputeRouter, NodeState, WorkloadKind, WorkloadRequest


def main() -> None:
    router = ComputeRouter()
    router.upsert_node(NodeState(id="node.alpha", capabilities=("gpu.inference",), cpu_cores=16, free_cpu_cores=10, memory_gb=64, free_memory_gb=40, gpu_vram_gb=12, free_vram_gb=8, gpu_utilization=0.2, queue_depth=1, latency_ms=25))
    decision = router.route(WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("gpu.inference",), estimated_vram_gb=2, interactive=True))
    assert decision.target_node == "node.alpha"
    assert decision.score > 0
    print("OK: Scheduler + Router MVP validation passed")


if __name__ == "__main__":
    main()
