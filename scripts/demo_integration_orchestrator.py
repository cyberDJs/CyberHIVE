#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.cache_reuse import CanonicalOperation, ExecutionCost
from cyberhive_core.data_fabric import DataFabric, DataObject, StorageDevice, StorageTier
from cyberhive_core.integration_orchestrator import IntegrationOrchestrator, OrchestrationRequest
from cyberhive_core.observations_forecasting import SchedulerHint, SchedulerHintAction
from cyberhive_core.scheduler_router import ComputeRouter, NodeState, WorkloadKind, WorkloadPriority, WorkloadRequest


def main() -> None:
    data = DataFabric()
    data.register_device(StorageDevice(id="ram-main", tier=StorageTier.L1_RAM, node_id="node.beta", capacity_bytes=32_000_000_000, used_bytes=8_000_000_000))
    data.register_device(StorageDevice(id="nvme-main", tier=StorageTier.L2_LOCAL_NVME, node_id="node.beta", capacity_bytes=2_000_000_000_000, used_bytes=600_000_000_000))
    data.register_object(
        DataObject(
            id="dataset.hot",
            size_bytes=32_000_000,
            reads_1h=180,
            reads_24h=900,
            latency_requirement="critical",
            exclusivity="high_fanout",
            predicted_use=0.85,
            reconstruction_seconds=3600,
            current_tier=StorageTier.L4_HDD_RAID,
        )
    )

    router = ComputeRouter()
    router.upsert_node(
        NodeState(
            id="node.alpha",
            capabilities=("model.infer",),
            cpu_cores=8,
            free_cpu_cores=2,
            memory_gb=32,
            free_memory_gb=10,
            gpu_vram_gb=8,
            free_vram_gb=2.5,
            gpu_utilization=0.70,
            queue_depth=5,
            latency_ms=35,
            data_locality=("dataset.logs",),
        )
    )
    router.upsert_node(
        NodeState(
            id="node.beta",
            capabilities=("model.infer", "data.move"),
            cpu_cores=12,
            free_cpu_cores=9,
            memory_gb=64,
            free_memory_gb=50,
            gpu_vram_gb=12,
            free_vram_gb=7,
            gpu_utilization=0.18,
            queue_depth=1,
            latency_ms=70,
            data_locality=("dataset.hot",),
        )
    )

    workload = WorkloadRequest(
        kind=WorkloadKind.INTERACTIVE_INFERENCE,
        required_capabilities=("model.infer",),
        priority=WorkloadPriority.HIGH,
        estimated_cpu_cores=1,
        estimated_memory_gb=2,
        estimated_vram_gb=2,
        interactive=True,
        latency_sensitive=True,
        model_id="llama-small",
        data_affinity=("dataset.hot",),
    )

    forecast_hint = SchedulerHint(
        action=SchedulerHintAction.PREWARM,
        target="node.beta",
        reason="queue depth is predicted to rise above threshold",
        priority=80,
    )

    plan = IntegrationOrchestrator(router=router, data_fabric=data).orchestrate(
        OrchestrationRequest(
            operation=CanonicalOperation(operation="model.answer", normalized_input={"prompt": "summarize"}, revision="demo"),
            workload=workload,
            data_object_ids=("dataset.hot",),
            scheduler_hints=(forecast_hint,),
            recompute_cost=ExecutionCost(cpu_ms=800, gpu_ms=3500, wall_ms=5000, token_count=1500, tool_calls=2),
            metadata={"demo": True},
        )
    )

    print(f"plan={plan.id} action={plan.action.value} reason={plan.reason}")
    if plan.route_decision:
        print(f"route: {plan.route_decision.action.value} target={plan.route_decision.target_node} score={plan.route_decision.score:.4f}")
        print(f"route reason: {plan.route_decision.reason}")
    for object_id, decision in plan.placement.items():
        print(f"placement: {object_id} {decision.action.value}->{decision.tier.value} targets={list(decision.target_devices)}")
    for move in plan.data_moves:
        print(f"data move candidate: {move.object_id} {move.action.value} {move.from_tier}->{move.to_tier.value}")
    for prewarm in plan.prewarm:
        print(f"prewarm: {prewarm.model_id} on {prewarm.target_node} priority={prewarm.priority}")
    print("steps: " + " | ".join(f"{step.name}:{step.status}" for step in plan.steps))


if __name__ == "__main__":
    main()
