#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.approval_workflow import ApprovalBroker, GovernedExecutionController
from cyberhive_core.cache_reuse import CanonicalOperation, ExecutionCost
from cyberhive_core.data_fabric import DataFabric, DataObject, StorageDevice, StorageTier
from cyberhive_core.integration_orchestrator import IntegrationOrchestrator, OrchestrationRequest
from cyberhive_core.observations_forecasting import SchedulerHint, SchedulerHintAction
from cyberhive_core.policy_governance import PolicyContext
from cyberhive_core.scheduler_router import ComputeRouter, NodeState, WorkloadKind, WorkloadPriority, WorkloadRequest


def build_plan():
    fabric = DataFabric()
    fabric.register_device(StorageDevice(id="ram-main", tier=StorageTier.L1_RAM, node_id="node.beta", capacity_bytes=32_000_000_000, used_bytes=8_000_000_000))
    fabric.register_device(StorageDevice(id="nvme-main", tier=StorageTier.L2_LOCAL_NVME, node_id="node.beta", capacity_bytes=2_000_000_000_000, used_bytes=500_000_000_000))
    fabric.register_object(DataObject(id="dataset.hot", size_bytes=10_000_000, reads_1h=200, reads_24h=1000, latency_requirement="critical", exclusivity="high_fanout", predicted_use=0.9, reconstruction_seconds=7200, current_tier=StorageTier.L4_HDD_RAID))

    router = ComputeRouter()
    router.upsert_node(NodeState(id="node.beta", capabilities=("model.infer", "data.move"), cpu_cores=12, free_cpu_cores=8, memory_gb=64, free_memory_gb=48, gpu_vram_gb=12, free_vram_gb=7, gpu_utilization=0.20, queue_depth=1, latency_ms=70, data_locality=("dataset.hot",)))

    workload = WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("model.infer",), priority=WorkloadPriority.HIGH, estimated_cpu_cores=1, estimated_memory_gb=2, estimated_vram_gb=2, interactive=True, latency_sensitive=True, model_id="llama-small", data_affinity=("dataset.hot",))
    request = OrchestrationRequest(
        operation=CanonicalOperation(operation="model.infer", normalized_input={"prompt":"hello"}, model_version="llama-small"),
        workload=workload,
        data_object_ids=("dataset.hot",),
        scheduler_hints=(SchedulerHint(action=SchedulerHintAction.PREWARM, target="node.beta", reason="forecast", priority=80),),
        recompute_cost=ExecutionCost(cpu_ms=200, wall_ms=300, token_count=100),
    )
    return IntegrationOrchestrator(data_fabric=fabric, router=router).orchestrate(request)


def main() -> None:
    plan = build_plan()
    broker = ApprovalBroker()
    controller = GovernedExecutionController(approval_broker=broker)

    pending = controller.evaluate_or_execute(plan, context=PolicyContext(subject="jan", dry_run=False))
    print(f"policy: {pending.outcome.value}")
    assert pending.approval_request is not None
    print("required:", ", ".join(pending.approval_request.required_tokens))

    approved = broker.approve(pending.approval_request.id, approver="jan", tokens=pending.approval_request.required_tokens, reason="local trusted dry-run promoted to live")
    print(f"approval: {approved.status.value} missing={list(approved.missing_tokens())}")

    executed = controller.resume_with_approval(plan, approval_request_id=approved.id, context=PolicyContext(subject="jan", dry_run=False))
    print(f"execution: {executed.outcome.value} run_status={executed.run.status.value if executed.run else 'none'}")
    if executed.run:
        for step in executed.run.steps:
            print(f"  {step.name}: {step.status.value}")


if __name__ == "__main__":
    main()
