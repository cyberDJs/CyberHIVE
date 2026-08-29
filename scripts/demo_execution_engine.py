#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from cyberhive_core.cache_reuse import CanonicalOperation, ExecutionCost
from cyberhive_core.data_fabric import DataFabric, DataObject, StorageDevice, StorageTier
from cyberhive_core.execution_engine import ExecutionEngine, ExecutionJournal
from cyberhive_core.integration_orchestrator import IntegrationOrchestrator, OrchestrationRequest
from cyberhive_core.log_store import AppendOnlyLog
from cyberhive_core.observations_forecasting import SchedulerHint, SchedulerHintAction
from cyberhive_core.runtime_bus import RuntimeBus
from cyberhive_core.scheduler_router import ComputeRouter, NodeState, WorkloadKind, WorkloadPriority, WorkloadRequest
from cyberhive_core.state_engine import StateEngine


def main() -> None:
    data = DataFabric()
    data.register_device(StorageDevice(id="ram-main", tier=StorageTier.L1_RAM, node_id="node.beta", capacity_bytes=32_000_000_000, used_bytes=8_000_000_000))
    data.register_object(DataObject(id="dataset.hot", size_bytes=64_000_000, reads_1h=180, reads_24h=900, latency_requirement="critical", exclusivity="high_fanout", predicted_use=0.85, reconstruction_seconds=3600, current_tier=StorageTier.L4_HDD_RAID))

    router = ComputeRouter()
    router.upsert_node(NodeState(id="node.beta", capabilities=("model.infer",), cpu_cores=12, free_cpu_cores=9, memory_gb=64, free_memory_gb=50, gpu_vram_gb=12, free_vram_gb=7, gpu_utilization=0.18, queue_depth=1, latency_ms=70, data_locality=("dataset.hot",)))

    workload = WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("model.infer",), priority=WorkloadPriority.HIGH, estimated_cpu_cores=1, estimated_memory_gb=2, estimated_vram_gb=2, interactive=True, latency_sensitive=True, model_id="llama-small", data_affinity=("dataset.hot",))
    request = OrchestrationRequest(
        operation=CanonicalOperation(operation="model.infer", normalized_input={"prompt":"beautiful ireland"}, model_version="llama-small"),
        workload=workload,
        data_object_ids=("dataset.hot",),
        scheduler_hints=(SchedulerHint(action=SchedulerHintAction.PREWARM, target="node.beta", reason="predicted queue pressure", priority=80),),
        recompute_cost=ExecutionCost(cpu_ms=300, wall_ms=500, token_count=200),
    )
    plan = IntegrationOrchestrator(data_fabric=data, router=router).orchestrate(request)

    with TemporaryDirectory() as tmp:
        bus = RuntimeBus(node_id="controller.local", log_store=AppendOnlyLog(Path(tmp) / "runtime.jsonl"), state_engine=StateEngine())
        journal = ExecutionJournal(Path(tmp) / "execution.jsonl")
        run = ExecutionEngine(runtime_bus=bus, journal=journal).execute(plan, dry_run=False)

        print(f"execution: {run.status.value} plan={run.plan_id} request={run.request_id}")
        for step in run.steps:
            print(f"step: {step.name} status={step.status.value}")
            print(f"  {step.reason}")
        print(f"events_published: {run.events_published}")
        print(f"journal_entries: {journal.count()}")
        print(f"runtime_frames: {bus.log_store.count()}")


if __name__ == "__main__":
    main()
