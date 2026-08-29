from __future__ import annotations

import unittest

from cyberhive_core.cache_reuse import CacheFabric, CanonicalOperation, ExecutionCost, ReuseAction, ReuseEngine
from cyberhive_core.data_fabric import DataFabric, DataObject, PlacementAction, StorageDevice, StorageTier
from cyberhive_core.integration_orchestrator import IntegrationOrchestrator, OrchestrationAction, OrchestrationRequest
from cyberhive_core.observations_forecasting import SchedulerHint, SchedulerHintAction
from cyberhive_core.scheduler_router import ComputeRouter, NodeState, RouteAction, WorkloadKind, WorkloadPriority, WorkloadRequest


class IntegrationOrchestratorMVPTest(unittest.TestCase):
    def _router(self) -> ComputeRouter:
        router = ComputeRouter()
        router.upsert_node(
            NodeState(
                id="node.alpha",
                capabilities=("model.infer",),
                cpu_cores=8,
                free_cpu_cores=2,
                memory_gb=32,
                free_memory_gb=8,
                gpu_vram_gb=8,
                free_vram_gb=2,
                gpu_utilization=0.75,
                queue_depth=5,
                latency_ms=40,
                data_locality=("dataset.logs",),
            )
        )
        router.upsert_node(
            NodeState(
                id="node.beta",
                capabilities=("model.infer", "data.move"),
                cpu_cores=12,
                free_cpu_cores=8,
                memory_gb=64,
                free_memory_gb=48,
                gpu_vram_gb=12,
                free_vram_gb=7,
                gpu_utilization=0.20,
                queue_depth=1,
                latency_ms=70,
                data_locality=("dataset.hot",),
            )
        )
        return router

    def _data_fabric(self) -> DataFabric:
        fabric = DataFabric()
        fabric.register_device(StorageDevice(id="ram-main", tier=StorageTier.L1_RAM, node_id="node.beta", capacity_bytes=32_000_000_000, used_bytes=8_000_000_000))
        fabric.register_device(StorageDevice(id="nvme-main", tier=StorageTier.L2_LOCAL_NVME, node_id="node.beta", capacity_bytes=2_000_000_000_000, used_bytes=500_000_000_000))
        fabric.register_object(
            DataObject(
                id="dataset.hot",
                size_bytes=10_000_000,
                reads_1h=200,
                reads_24h=1000,
                latency_requirement="critical",
                exclusivity="high_fanout",
                predicted_use=0.9,
                reconstruction_seconds=7200,
                current_tier=StorageTier.L4_HDD_RAID,
            )
        )
        return fabric

    def _workload(self) -> WorkloadRequest:
        return WorkloadRequest(
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

    def test_exact_cache_hit_skips_routing(self) -> None:
        cache = CacheFabric()
        operation = CanonicalOperation(operation="model.answer", normalized_input={"q": "status"}, revision="r1")
        cache.put_exact(operation, {"answer": "cached"}, ttl_seconds=60)
        orchestrator = IntegrationOrchestrator(reuse_engine=ReuseEngine(cache), router=self._router(), data_fabric=self._data_fabric())

        plan = orchestrator.orchestrate(
            OrchestrationRequest(
                operation=operation,
                workload=self._workload(),
                recompute_cost=ExecutionCost(wall_ms=5000, token_count=2000, tool_calls=2),
            )
        )

        self.assertEqual(plan.action, OrchestrationAction.REUSE)
        self.assertIsNone(plan.route_decision)
        self.assertIsNotNone(plan.reuse_decision)
        self.assertEqual(plan.reuse_decision.action, ReuseAction.REUSE_EXACT)

    def test_cache_miss_routes_and_plans_data(self) -> None:
        orchestrator = IntegrationOrchestrator(router=self._router(), data_fabric=self._data_fabric())
        plan = orchestrator.orchestrate(
            OrchestrationRequest(
                operation=CanonicalOperation(operation="model.answer", normalized_input={"q": "new"}, revision="r1"),
                workload=self._workload(),
                data_object_ids=("dataset.hot",),
                recompute_cost=ExecutionCost(wall_ms=5000, token_count=2000),
            )
        )

        self.assertIn(plan.action, {OrchestrationAction.ROUTE, OrchestrationAction.PREWARM})
        self.assertIsNotNone(plan.route_decision)
        self.assertEqual(plan.route_decision.target_node, "node.beta")
        self.assertIn("dataset.hot", plan.placement)
        self.assertEqual(plan.placement["dataset.hot"].action, PlacementAction.PROMOTE)
        self.assertTrue(plan.data_moves)

    def test_forecast_hint_becomes_router_hint_and_prewarm_plan(self) -> None:
        orchestrator = IntegrationOrchestrator(router=self._router(), data_fabric=self._data_fabric())
        workload = self._workload()
        hint = SchedulerHint(
            action=SchedulerHintAction.PREWARM,
            target="node.beta",
            reason="queue depth is predicted to rise",
            priority=80,
            metadata={},
        )

        plan = orchestrator.orchestrate(
            OrchestrationRequest(
                operation=CanonicalOperation(operation="model.answer", normalized_input={"q": "forecast"}, revision="r1"),
                workload=workload,
                scheduler_hints=(hint,),
                allow_reuse=False,
            )
        )

        self.assertEqual(plan.scheduler_hints[0].metadata["model_id"], "llama-small")
        self.assertTrue(plan.prewarm)
        self.assertEqual(plan.prewarm[0].target_node, "node.beta")
        self.assertEqual(plan.prewarm[0].model_id, "llama-small")

    def test_mapping_hint_is_supported(self) -> None:
        orchestrator = IntegrationOrchestrator(router=self._router(), data_fabric=self._data_fabric())
        plan = orchestrator.orchestrate(
            OrchestrationRequest(
                operation=CanonicalOperation(operation="batch.index", revision="r1"),
                workload=WorkloadRequest(
                    kind=WorkloadKind.BATCH_INFERENCE,
                    required_capabilities=("model.infer",),
                    estimated_cpu_cores=1,
                    estimated_memory_gb=1,
                    estimated_vram_gb=1,
                    model_id="llama-small",
                ),
                scheduler_hints=({"action": "shift_load", "target": "node.alpha", "priority": 70, "reason": "forecast pressure"},),
                allow_reuse=False,
            )
        )
        self.assertIsNotNone(plan.route_decision)
        self.assertEqual(plan.scheduler_hints[0].action.value, "shift_load")

    def test_no_nodes_rejects(self) -> None:
        orchestrator = IntegrationOrchestrator(router=ComputeRouter(), data_fabric=self._data_fabric())
        plan = orchestrator.orchestrate(
            OrchestrationRequest(
                operation=CanonicalOperation(operation="model.answer", revision="r1"),
                workload=self._workload(),
                allow_reuse=False,
            )
        )
        self.assertEqual(plan.action, OrchestrationAction.REJECT)
        self.assertEqual(plan.route_decision.action, RouteAction.REJECT)

    def test_as_dict_contains_all_major_sections(self) -> None:
        orchestrator = IntegrationOrchestrator(router=self._router(), data_fabric=self._data_fabric())
        plan = orchestrator.orchestrate(
            OrchestrationRequest(
                operation=CanonicalOperation(operation="model.answer", revision="r1"),
                workload=self._workload(),
                data_object_ids=("dataset.hot",),
                allow_reuse=False,
            )
        )
        payload = plan.as_dict()
        self.assertIn("route_decision", payload)
        self.assertIn("placement", payload)
        self.assertIn("data_moves", payload)
        self.assertIn("steps", payload)
        self.assertEqual(payload["request_id"], plan.request_id)

    def test_negative_freshness_tolerance_is_rejected(self) -> None:
        orchestrator = IntegrationOrchestrator(router=self._router(), data_fabric=self._data_fabric())
        with self.assertRaises(ValueError):
            orchestrator.orchestrate(
                OrchestrationRequest(
                    operation=CanonicalOperation(operation="model.answer", revision="r1"),
                    workload=self._workload(),
                    freshness_tolerance_seconds=-1,
                )
            )


if __name__ == "__main__":
    unittest.main()
