from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cyberhive_core.cache_reuse import CacheFabric, CanonicalOperation, ExecutionCost, ReuseEngine
from cyberhive_core.data_fabric import DataFabric, DataObject, StorageDevice, StorageTier
from cyberhive_core.execution_engine import ExecutionEngine, ExecutionJournal, ExecutionPolicy, ExecutionStatus
from cyberhive_core.integration_orchestrator import IntegrationOrchestrator, OrchestrationAction, OrchestrationRequest
from cyberhive_core.log_store import AppendOnlyLog
from cyberhive_core.observations_forecasting import SchedulerHint, SchedulerHintAction
from cyberhive_core.runtime_bus import RuntimeBus
from cyberhive_core.scheduler_router import ComputeRouter, NodeState, WorkloadKind, WorkloadPriority, WorkloadRequest
from cyberhive_core.state_engine import StateEngine


class ExecutionEngineMVPTest(unittest.TestCase):
    def _data(self) -> DataFabric:
        fabric = DataFabric()
        fabric.register_device(StorageDevice(id="ram-main", tier=StorageTier.L1_RAM, node_id="node.beta", capacity_bytes=32_000_000_000, used_bytes=8_000_000_000))
        fabric.register_device(StorageDevice(id="nvme-main", tier=StorageTier.L2_LOCAL_NVME, node_id="node.beta", capacity_bytes=2_000_000_000_000, used_bytes=500_000_000_000))
        fabric.register_object(DataObject(id="dataset.hot", size_bytes=10_000_000, reads_1h=200, reads_24h=1000, latency_requirement="critical", exclusivity="high_fanout", predicted_use=0.9, reconstruction_seconds=7200, current_tier=StorageTier.L4_HDD_RAID))
        return fabric

    def _router(self) -> ComputeRouter:
        router = ComputeRouter()
        router.upsert_node(NodeState(id="node.beta", capabilities=("model.infer", "data.move"), cpu_cores=12, free_cpu_cores=8, memory_gb=64, free_memory_gb=48, gpu_vram_gb=12, free_vram_gb=7, gpu_utilization=0.20, queue_depth=1, latency_ms=70, data_locality=("dataset.hot",)))
        return router

    def _workload(self) -> WorkloadRequest:
        return WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("model.infer",), priority=WorkloadPriority.HIGH, estimated_cpu_cores=1, estimated_memory_gb=2, estimated_vram_gb=2, interactive=True, latency_sensitive=True, model_id="llama-small", data_affinity=("dataset.hot",))

    def _plan(self):
        request = OrchestrationRequest(
            operation=CanonicalOperation(operation="model.infer", normalized_input={"prompt":"hello"}, model_version="llama-small"),
            workload=self._workload(),
            data_object_ids=("dataset.hot",),
            scheduler_hints=(SchedulerHint(action=SchedulerHintAction.PREWARM, target="node.beta", reason="forecast", priority=80),),
            recompute_cost=ExecutionCost(cpu_ms=200, wall_ms=300, token_count=100),
        )
        return IntegrationOrchestrator(data_fabric=self._data(), router=self._router()).orchestrate(request)

    def test_dry_run_records_all_steps_without_side_effect_status(self) -> None:
        plan = self._plan()
        run = ExecutionEngine().execute(plan, dry_run=True)
        self.assertEqual(run.status, ExecutionStatus.DRY_RUN)
        self.assertEqual(len(run.steps), len(plan.steps))
        self.assertTrue(all(step.status == ExecutionStatus.DRY_RUN for step in run.steps))

    def test_live_execution_is_non_destructive_and_succeeds(self) -> None:
        plan = self._plan()
        run = ExecutionEngine().execute(plan, dry_run=False)
        self.assertEqual(run.status, ExecutionStatus.SUCCEEDED)
        statuses = {step.name: step.status for step in run.steps}
        self.assertEqual(statuses["route"], ExecutionStatus.SUCCEEDED)
        self.assertEqual(statuses["data_moves"], ExecutionStatus.SKIPPED)
        self.assertEqual(statuses["prewarm"], ExecutionStatus.SKIPPED)

    def test_policy_can_allow_prewarm_step(self) -> None:
        plan = self._plan()
        run = ExecutionEngine(policy=ExecutionPolicy(allow_prewarm_side_effects=True)).execute(plan, dry_run=False)
        statuses = {step.name: step.status for step in run.steps}
        self.assertEqual(statuses["prewarm"], ExecutionStatus.SUCCEEDED)

    def test_journal_and_runtime_bus_receive_lifecycle_events(self) -> None:
        plan = self._plan()
        with TemporaryDirectory() as tmp:
            bus = RuntimeBus(node_id="controller.local", log_store=AppendOnlyLog(Path(tmp) / "runtime.jsonl"), state_engine=StateEngine())
            journal = ExecutionJournal(Path(tmp) / "execution.jsonl")
            run = ExecutionEngine(runtime_bus=bus, journal=journal).execute(plan, dry_run=False)
            self.assertEqual(run.events_published, 2)
            self.assertEqual(journal.count(), 1)
            self.assertEqual(bus.log_store.count(), 1)
            self.assertEqual(bus.state_engine.revision, 2)

    def test_reuse_plan_skips_compute(self) -> None:
        fabric = CacheFabric()
        operation = CanonicalOperation(operation="model.infer", normalized_input={"prompt":"cached"}, model_version="llama-small")
        fabric.put_exact(operation, {"text":"cached answer"})
        reuse = ReuseEngine(cache=fabric)
        request = OrchestrationRequest(operation=operation, workload=self._workload(), recompute_cost=ExecutionCost(cpu_ms=500, wall_ms=1000, token_count=500))
        plan = IntegrationOrchestrator(reuse_engine=reuse, data_fabric=self._data(), router=self._router()).orchestrate(request)
        self.assertEqual(plan.action, OrchestrationAction.REUSE)
        run = ExecutionEngine().execute(plan, dry_run=False)
        self.assertEqual(run.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(run.steps[0].name, "reuse")
        self.assertEqual(run.steps[0].status, ExecutionStatus.SUCCEEDED)


if __name__ == "__main__":
    unittest.main()
