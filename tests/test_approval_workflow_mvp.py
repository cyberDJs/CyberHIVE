from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cyberhive_core.approval_workflow import (
    ApprovalBroker,
    ApprovalJournal,
    ApprovalStatus,
    GovernedExecutionController,
    GovernedExecutionOutcome,
)
from cyberhive_core.cache_reuse import CanonicalOperation, ExecutionCost
from cyberhive_core.data_fabric import DataFabric, DataObject, StorageDevice, StorageTier
from cyberhive_core.integration_orchestrator import IntegrationOrchestrator, OrchestrationRequest
from cyberhive_core.observations_forecasting import SchedulerHint, SchedulerHintAction
from cyberhive_core.policy_governance import ApprovalToken, PolicyContext, PolicyGuard, PolicyOutcome
from cyberhive_core.scheduler_router import ComputeRouter, NodeState, WorkloadKind, WorkloadPriority, WorkloadRequest


class ApprovalWorkflowMvpTests(unittest.TestCase):
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

    def test_broker_creates_request_from_policy_decision(self) -> None:
        plan = self._plan()
        decision = PolicyGuard().evaluate_plan(plan, PolicyContext(subject="jan", dry_run=False))
        self.assertEqual(decision.outcome, PolicyOutcome.REQUIRE_APPROVAL)
        request = ApprovalBroker().create_request(decision, requested_by="jan")
        self.assertEqual(request.status, ApprovalStatus.OPEN)
        self.assertIn(ApprovalToken.EXECUTE_LIVE.value, request.required_tokens)
        self.assertIn(ApprovalToken.DATA_MOVE_EXECUTE.value, request.required_tokens)
        self.assertIn(ApprovalToken.PREWARM_EXECUTE.value, request.required_tokens)

    def test_partial_and_full_approval_statuses(self) -> None:
        plan = self._plan()
        decision = PolicyGuard().evaluate_plan(plan, PolicyContext(subject="jan", dry_run=False))
        broker = ApprovalBroker()
        request = broker.create_request(decision, requested_by="jan")
        partial = broker.approve(request.id, approver="eimy", tokens=(ApprovalToken.EXECUTE_LIVE,))
        self.assertEqual(partial.status, ApprovalStatus.PARTIALLY_APPROVED)
        self.assertIn(ApprovalToken.DATA_MOVE_EXECUTE.value, partial.missing_tokens())
        full = broker.approve(request.id, approver="eimy", tokens=partial.missing_tokens())
        self.assertEqual(full.status, ApprovalStatus.APPROVED)
        self.assertEqual(full.missing_tokens(), ())

    def test_governed_controller_executes_dry_run_without_approval(self) -> None:
        result = GovernedExecutionController().evaluate_or_execute(
            self._plan(),
            context=PolicyContext(subject="jan", dry_run=True),
        )
        self.assertEqual(result.outcome, GovernedExecutionOutcome.DRY_RUN)
        self.assertIsNotNone(result.run)
        self.assertIsNone(result.approval_request)

    def test_governed_controller_creates_approval_request_for_live_run(self) -> None:
        result = GovernedExecutionController().evaluate_or_execute(
            self._plan(),
            context=PolicyContext(subject="jan", dry_run=False),
        )
        self.assertEqual(result.outcome, GovernedExecutionOutcome.APPROVAL_REQUIRED)
        self.assertIsNotNone(result.approval_request)
        self.assertIsNone(result.run)

    def test_resume_with_approved_tokens_executes_live_with_side_effect_policy(self) -> None:
        plan = self._plan()
        broker = ApprovalBroker()
        controller = GovernedExecutionController(approval_broker=broker)
        pending = controller.evaluate_or_execute(plan, context=PolicyContext(subject="jan", dry_run=False))
        assert pending.approval_request is not None
        broker.approve(pending.approval_request.id, approver="jan", tokens=pending.approval_request.required_tokens)
        result = controller.resume_with_approval(
            plan,
            approval_request_id=pending.approval_request.id,
            context=PolicyContext(subject="jan", dry_run=False),
        )
        self.assertEqual(result.outcome, GovernedExecutionOutcome.EXECUTED)
        self.assertIsNotNone(result.run)
        statuses = {step.name: step.status.value for step in result.run.steps}
        self.assertEqual(statuses["data_moves"], "succeeded")
        self.assertEqual(statuses["prewarm"], "succeeded")

    def test_journal_records_approval_events(self) -> None:
        plan = self._plan()
        decision = PolicyGuard().evaluate_plan(plan, PolicyContext(subject="jan", dry_run=False))
        with TemporaryDirectory() as tmp:
            journal = ApprovalJournal(Path(tmp) / "approvals.jsonl")
            broker = ApprovalBroker(journal=journal)
            request = broker.create_request(decision, requested_by="jan")
            broker.approve(request.id, approver="eimy", tokens=request.required_tokens)
            self.assertEqual(journal.count(), 2)
            self.assertEqual(journal.iter_events()[0]["event_type"], "approval.created")


if __name__ == "__main__":
    unittest.main()
