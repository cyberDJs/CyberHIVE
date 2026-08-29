#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone

from cyberhive_core.data_fabric import DataMove, PlacementAction, StorageTier
from cyberhive_core.integration_orchestrator import OrchestrationAction, OrchestrationPlan
from cyberhive_core.policy_governance import ApprovalToken, PolicyContext, PolicyGuard
from cyberhive_core.scheduler_router import RouteAction, RouteDecision


def main() -> None:
    move = DataMove(
        object_id="dataset.session.current",
        action=PlacementAction.PROMOTE,
        from_tier=StorageTier.L4_HDD_RAID,
        to_tier=StorageTier.L2_LOCAL_NVME,
        replicas=1,
        target_devices=("nvme-a",),
        reason="hot data before execution",
    )
    plan = OrchestrationPlan(
        id="orch_demo_policy",
        request_id="wl_demo_policy",
        action=OrchestrationAction.PREWARM,
        reason="forecast predicts queue pressure",
        created_at=datetime.now(timezone.utc),
        route_decision=RouteDecision(
            request_id="wl_demo_policy",
            action=RouteAction.PREWARM,
            target_node="node.beta",
            score=0.7605,
            reason="hint=prewarm; free_vram_after=5.00GB",
            prewarm=("llama-small",),
        ),
        data_moves=(move,),
        metadata={"classification": "internal"},
    )

    guard = PolicyGuard()
    dry = guard.evaluate_plan(plan, PolicyContext(subject="jan", dry_run=True))
    live = guard.evaluate_plan(plan, PolicyContext(subject="jan", dry_run=False))
    approved = guard.evaluate_plan(
        plan,
        PolicyContext(
            subject="jan",
            dry_run=False,
            approvals=(
                ApprovalToken.EXECUTE_LIVE.value,
                ApprovalToken.DATA_MOVE_EXECUTE.value,
                ApprovalToken.PREWARM_EXECUTE.value,
            ),
        ),
    )

    print(f"dry-run: {dry.outcome.value} approvals={dry.required_approvals()}")
    print(f"live: {live.outcome.value} approvals={live.required_approvals()}")
    print(f"approved: {approved.outcome.value} approvals={approved.required_approvals()}")


if __name__ == "__main__":
    main()
