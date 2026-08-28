from __future__ import annotations

from datetime import datetime, timezone
import unittest

from cyberhive_core.data_fabric import DataMove, PlacementAction, StorageTier
from cyberhive_core.integration_orchestrator import OrchestrationAction, OrchestrationPlan
from cyberhive_core.node_agent import (
    AgentActionRequest,
    AgentActionStatus,
    AgentActionType,
    LocalNodeAgent,
    NodeActionDispatcher,
    NodeAgentError,
    NodeAgentPolicy,
    NodeAgentRegistry,
    NodeDescriptor,
)
from cyberhive_core.scheduler_router import PrewarmPlan, RouteAction, RouteDecision


class NodeAgentMvpTests(unittest.TestCase):
    def test_dry_run_prewarm_has_no_side_effect(self) -> None:
        agent = LocalNodeAgent(
            NodeDescriptor(
                id="node.alpha",
                allowed_actions=(AgentActionType.HEALTH_CHECK, AgentActionType.PREWARM_MODEL),
            )
        )
        result = agent.handle(
            AgentActionRequest(
                target_node="node.alpha",
                action=AgentActionType.PREWARM_MODEL,
                payload={"model_id": "llama-small"},
                dry_run=True,
            )
        )
        self.assertEqual(result.status, AgentActionStatus.DRY_RUN)
        self.assertNotIn("llama-small", agent.warmed_models)

    def test_live_prewarm_requires_policy_and_token(self) -> None:
        agent = LocalNodeAgent(
            NodeDescriptor(id="node.alpha", allowed_actions=(AgentActionType.PREWARM_MODEL,)),
            policy=NodeAgentPolicy(allow_live_actions=True, allow_prewarm=True),
        )
        denied = agent.handle(
            AgentActionRequest(
                target_node="node.alpha",
                action=AgentActionType.PREWARM_MODEL,
                payload={"model_id": "llama-small"},
                dry_run=False,
            )
        )
        self.assertEqual(denied.status, AgentActionStatus.DENIED)

        allowed = agent.handle(
            AgentActionRequest(
                target_node="node.alpha",
                action=AgentActionType.PREWARM_MODEL,
                payload={"model_id": "llama-small"},
                dry_run=False,
                approval_tokens=("runtime.prewarm.execute",),
            )
        )
        self.assertEqual(allowed.status, AgentActionStatus.SUCCEEDED)
        self.assertIn("llama-small", agent.warmed_models)

    def test_registry_dispatches_to_target_node(self) -> None:
        registry = NodeAgentRegistry()
        registry.register(LocalNodeAgent(NodeDescriptor(id="node.alpha", allowed_actions=(AgentActionType.HEALTH_CHECK,))))
        result = registry.dispatch(AgentActionRequest(target_node="node.alpha", action=AgentActionType.HEALTH_CHECK))
        self.assertEqual(result.status, AgentActionStatus.DRY_RUN)
        with self.assertRaises(NodeAgentError):
            registry.dispatch(AgentActionRequest(target_node="node.missing", action=AgentActionType.HEALTH_CHECK))

    def test_plan_dispatch_builds_prewarm_and_data_move_requests(self) -> None:
        plan = OrchestrationPlan(
            id="orch_test",
            request_id="wl_test",
            action=OrchestrationAction.PREWARM,
            reason="test",
            created_at=datetime.now(timezone.utc),
            route_decision=RouteDecision(
                request_id="wl_test",
                action=RouteAction.PREWARM,
                target_node="node.beta",
                score=0.7,
                reason="test route",
            ),
            prewarm=(
                PrewarmPlan(
                    id="pw_1",
                    target_node="node.beta",
                    model_id="llama-small",
                    reason="forecast says queue rises",
                    priority=80,
                    actions=("load_model",),
                ),
            ),
            data_moves=(
                DataMove(
                    object_id="dataset.hot",
                    action=PlacementAction.PROMOTE,
                    from_tier=StorageTier.L4_HDD_RAID,
                    to_tier=StorageTier.L2_LOCAL_NVME,
                    replicas=1,
                    target_devices=("nvme-beta",),
                    reason="move closer to compute",
                ),
            ),
        )
        registry = NodeAgentRegistry()
        registry.register(
            LocalNodeAgent(
                NodeDescriptor(
                    id="node.beta",
                    allowed_actions=(AgentActionType.PREWARM_MODEL, AgentActionType.DATA_MOVE),
                )
            )
        )
        dispatcher = NodeActionDispatcher(registry)
        requests = dispatcher.build_requests(plan)
        self.assertEqual(len(requests), 2)
        self.assertEqual({request.action for request in requests}, {AgentActionType.PREWARM_MODEL, AgentActionType.DATA_MOVE})

        results = dispatcher.dispatch_plan(plan)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.status == AgentActionStatus.DRY_RUN for result in results))

    def test_payload_size_limit_is_enforced(self) -> None:
        agent = LocalNodeAgent(
            NodeDescriptor(id="node.alpha", allowed_actions=(AgentActionType.CACHE_PRIME,)),
            policy=NodeAgentPolicy(max_payload_bytes=16),
        )
        result = agent.handle(
            AgentActionRequest(
                target_node="node.alpha",
                action=AgentActionType.CACHE_PRIME,
                payload={"large": "x" * 100},
            )
        )
        self.assertEqual(result.status, AgentActionStatus.DENIED)
        self.assertIn("payload exceeds", result.reason)

    def test_disabled_node_denies_actions(self) -> None:
        agent = LocalNodeAgent(NodeDescriptor(id="node.alpha", enabled=False, allowed_actions=(AgentActionType.HEALTH_CHECK,)))
        result = agent.handle(AgentActionRequest(target_node="node.alpha", action=AgentActionType.HEALTH_CHECK))
        self.assertEqual(result.status, AgentActionStatus.DENIED)


if __name__ == "__main__":
    unittest.main()
