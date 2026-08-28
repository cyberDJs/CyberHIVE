#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone

from cyberhive_core.data_fabric import DataMove, PlacementAction, StorageTier
from cyberhive_core.integration_orchestrator import OrchestrationAction, OrchestrationPlan
from cyberhive_core.node_agent import (
    AgentActionType,
    LocalNodeAgent,
    NodeActionDispatcher,
    NodeAgentPolicy,
    NodeAgentRegistry,
    NodeDescriptor,
)
from cyberhive_core.scheduler_router import PrewarmPlan, RouteAction, RouteDecision


def main() -> None:
    registry = NodeAgentRegistry()
    registry.register(
        LocalNodeAgent(
            NodeDescriptor(
                id="node.beta",
                capabilities=("gpu.nvidia", "model.prewarm", "data.move.intent"),
                allowed_actions=(AgentActionType.PREWARM_MODEL, AgentActionType.DATA_MOVE, AgentActionType.HEALTH_CHECK),
            ),
            policy=NodeAgentPolicy(allow_live_actions=True, allow_prewarm=True, allow_data_moves=True),
        )
    )

    plan = OrchestrationPlan(
        id="orch_demo",
        request_id="wl_demo",
        action=OrchestrationAction.PREWARM,
        reason="forecasted pressure; prepare node before execution",
        created_at=datetime.now(timezone.utc),
        route_decision=RouteDecision(
            request_id="wl_demo",
            action=RouteAction.PREWARM,
            target_node="node.beta",
            score=0.7605,
            reason="hint=prewarm; free_vram_after=5.00GB",
        ),
        prewarm=(
            PrewarmPlan(
                id="pw_demo",
                target_node="node.beta",
                model_id="llama-small",
                reason="queue depth is predicted to rise above threshold",
                priority=80,
                actions=("load_model", "reserve_vram"),
            ),
        ),
        data_moves=(
            DataMove(
                object_id="dataset.session.current",
                action=PlacementAction.PROMOTE,
                from_tier=StorageTier.L4_HDD_RAID,
                to_tier=StorageTier.L2_LOCAL_NVME,
                replicas=1,
                target_devices=("nvme-beta",),
                reason="move data closer to selected compute node",
            ),
        ),
    )

    dispatcher = NodeActionDispatcher(registry)
    dry = dispatcher.dispatch_plan(plan, dry_run=True)
    print("dry-run:")
    for result in dry:
        print(f"  {result.action.value} -> {result.status.value}: {result.reason}")

    live = dispatcher.dispatch_plan(
        plan,
        dry_run=False,
        approval_tokens=("runtime.prewarm.execute", "data.move.execute"),
        requested_by="johnny",
    )
    print("live approved:")
    for result in live:
        print(f"  {result.action.value} -> {result.status.value}: {result.reason}")


if __name__ == "__main__":
    main()
