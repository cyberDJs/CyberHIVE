#!/usr/bin/env python3
from cyberhive_core.scheduler_router import (
    ComputeRouter,
    HintAction,
    NodeState,
    PrewarmPlanner,
    SchedulerHintImpact,
    WorkloadKind,
    WorkloadRequest,
)


def main() -> None:
    nodes = [
        NodeState(id="node.alpha", capabilities=("gpu.inference",), cpu_cores=16, free_cpu_cores=10, memory_gb=64, free_memory_gb=40, gpu_vram_gb=12, free_vram_gb=6, gpu_utilization=0.72, queue_depth=5, latency_ms=40),
        NodeState(id="node.beta", capabilities=("gpu.inference",), cpu_cores=12, free_cpu_cores=8, memory_gb=48, free_memory_gb=28, gpu_vram_gb=10, free_vram_gb=7, gpu_utilization=0.35, queue_depth=1, latency_ms=55),
    ]
    hints = [
        SchedulerHintImpact(action=HintAction.HOLD_CAPACITY, target="node.alpha", priority=85, reason="predicted free VRAM is low"),
        SchedulerHintImpact(action=HintAction.PREWARM, target="node.beta", priority=80, reason="queue depth is predicted to rise", metadata={"model_id": "llama-small"}),
        SchedulerHintImpact(action=HintAction.SHIFT_LOAD, target="node.alpha", priority=70, reason="route non-interactive work away before pressure peaks"),
    ]
    router = ComputeRouter()
    for node in nodes:
        router.upsert_node(node)
    router.set_hints(hints)

    workload = WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("gpu.inference",), estimated_vram_gb=2, interactive=True, latency_sensitive=True, model_id="llama-small")
    decision = router.route(workload)
    print(f"decision: {decision.action.value} target={decision.target_node} score={decision.score:.4f}")
    print(f"reason: {decision.reason}")
    for alt in sorted(decision.alternatives, key=lambda item: item.score, reverse=True):
        print(f"alternative: {alt.node_id} score={alt.score:.4f} eligible={alt.eligible}")

    plans = PrewarmPlanner().build_plans(hints=hints, workloads=[workload], nodes=nodes)
    for plan in plans:
        print(f"prewarm: {plan.model_id} on {plan.target_node} priority={plan.priority}")


if __name__ == "__main__":
    main()
