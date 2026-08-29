import unittest

from cyberhive_core.scheduler_router import (
    ComputeRouter,
    HintAction,
    NodeState,
    PrewarmPlanner,
    RouteAction,
    SchedulerHintImpact,
    WorkloadKind,
    WorkloadPriority,
    WorkloadRequest,
)


class SchedulerRouterMvpTests(unittest.TestCase):
    def test_routes_interactive_workload_to_best_gpu_node(self):
        router = ComputeRouter()
        router.upsert_node(NodeState(id="node.slow", capabilities=("gpu.inference",), cpu_cores=8, free_cpu_cores=4, memory_gb=32, free_memory_gb=10, gpu_vram_gb=8, free_vram_gb=1.5, gpu_utilization=0.7, queue_depth=4, latency_ms=120))
        router.upsert_node(NodeState(id="node.fast", capabilities=("gpu.inference",), cpu_cores=16, free_cpu_cores=10, memory_gb=64, free_memory_gb=40, gpu_vram_gb=12, free_vram_gb=7, gpu_utilization=0.2, queue_depth=1, latency_ms=30))

        decision = router.route(WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("gpu.inference",), estimated_vram_gb=3, interactive=True, latency_sensitive=True))

        self.assertEqual(decision.action, RouteAction.ROUTE)
        self.assertEqual(decision.target_node, "node.fast")
        self.assertGreater(decision.score, 0.5)

    def test_rejects_when_capability_is_missing(self):
        router = ComputeRouter()
        router.upsert_node(NodeState(id="node.cpu", capabilities=("cpu.batch",), cpu_cores=8, free_cpu_cores=8, memory_gb=16, free_memory_gb=16))

        decision = router.route(WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("gpu.inference",)))

        self.assertEqual(decision.action, RouteAction.REJECT)
        self.assertIsNone(decision.target_node)
        self.assertTrue(decision.queue)

    def test_interactive_vram_reserve_is_enforced(self):
        router = ComputeRouter(minimum_interactive_vram_headroom_gb=1.0)
        router.upsert_node(NodeState(id="node.tight", capabilities=("gpu.inference",), cpu_cores=8, free_cpu_cores=8, memory_gb=32, free_memory_gb=24, gpu_vram_gb=8, free_vram_gb=3.5))

        decision = router.route(WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("gpu.inference",), estimated_vram_gb=3.0, interactive=True))

        self.assertEqual(decision.action, RouteAction.REJECT)
        self.assertIn("interactive VRAM reserve", decision.reason)

    def test_hints_shift_background_load_away(self):
        router = ComputeRouter()
        router.upsert_node(NodeState(id="node.alpha", capabilities=("gpu.inference",), cpu_cores=16, free_cpu_cores=12, memory_gb=64, free_memory_gb=48, gpu_vram_gb=12, free_vram_gb=8, gpu_utilization=0.2, queue_depth=1, latency_ms=20))
        router.upsert_node(NodeState(id="node.beta", capabilities=("gpu.inference",), cpu_cores=16, free_cpu_cores=10, memory_gb=64, free_memory_gb=44, gpu_vram_gb=12, free_vram_gb=7, gpu_utilization=0.3, queue_depth=1, latency_ms=25))
        router.set_hints([SchedulerHintImpact(action=HintAction.SHIFT_LOAD, target="node.alpha", priority=100, reason="interactive pressure predicted")])

        decision = router.route(WorkloadRequest(kind=WorkloadKind.BATCH_INFERENCE, required_capabilities=("gpu.inference",), estimated_vram_gb=2, interactive=False))

        self.assertEqual(decision.target_node, "node.beta")

    def test_critical_work_can_ignore_hold_capacity_penalty(self):
        router = ComputeRouter()
        router.upsert_node(NodeState(id="node.alpha", capabilities=("gpu.inference",), cpu_cores=16, free_cpu_cores=12, memory_gb=64, free_memory_gb=48, gpu_vram_gb=12, free_vram_gb=8, gpu_utilization=0.2, queue_depth=1, latency_ms=20))
        router.set_hints([{"action": "hold_capacity", "target": "node.alpha", "priority": 100, "reason": "reserve headroom"}])

        decision = router.route(WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("gpu.inference",), estimated_vram_gb=1, interactive=True, priority=WorkloadPriority.CRITICAL))

        self.assertEqual(decision.action, RouteAction.ROUTE)
        self.assertEqual(decision.target_node, "node.alpha")

    def test_prewarm_hint_can_create_prewarm_route_action(self):
        router = ComputeRouter()
        router.upsert_node(NodeState(id="node.alpha", capabilities=("gpu.inference",), cpu_cores=16, free_cpu_cores=12, memory_gb=64, free_memory_gb=48, gpu_vram_gb=12, free_vram_gb=8, gpu_utilization=0.2, queue_depth=1, latency_ms=20))
        router.set_hints([SchedulerHintImpact(action=HintAction.PREWARM, target="node.alpha", priority=80, reason="queue rising", metadata={"model_id": "llama-small"})])

        decision = router.route(WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("gpu.inference",), estimated_vram_gb=2, interactive=True, model_id="llama-small"))

        self.assertEqual(decision.action, RouteAction.PREWARM)
        self.assertEqual(decision.prewarm, ("llama-small",))

    def test_prewarm_planner_builds_ordered_plans(self):
        planner = PrewarmPlanner()
        plans = planner.build_plans(
            hints=[SchedulerHintImpact(action=HintAction.PREWARM, target="node.alpha", priority=80, reason="queue rising", metadata={"model_id": "llama-small"})],
            workloads=[WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, model_id="llama-small")],
            nodes=[NodeState(id="node.alpha", enabled=True, healthy=True)],
        )

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].target_node, "node.alpha")
        self.assertEqual(plans[0].model_id, "llama-small")
        self.assertIn("load model weights", plans[0].actions)

    def test_labels_and_data_affinity_influence_decision(self):
        router = ComputeRouter()
        router.upsert_node(NodeState(id="node.a", capabilities=("data.local",), labels={"site": "home"}, cpu_cores=8, free_cpu_cores=5, memory_gb=32, free_memory_gb=16, data_locality=("dataset.logs",), latency_ms=30))
        router.upsert_node(NodeState(id="node.b", capabilities=("data.local",), labels={"site": "remote"}, cpu_cores=8, free_cpu_cores=8, memory_gb=32, free_memory_gb=30, data_locality=(), latency_ms=10))

        decision = router.route(WorkloadRequest(kind=WorkloadKind.INDEXING, required_capabilities=("data.local",), labels_required={"site": "home"}, data_affinity=("dataset.logs",)))

        self.assertEqual(decision.target_node, "node.a")
        self.assertIn("data affinity match", decision.reason)


if __name__ == "__main__":
    unittest.main()
