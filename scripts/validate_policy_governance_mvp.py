#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone

from cyberhive_core.integration_orchestrator import OrchestrationAction, OrchestrationPlan
from cyberhive_core.policy_governance import ApprovalToken, PolicyContext, PolicyGuard, PolicyOutcome
from cyberhive_core.scheduler_router import RouteAction, RouteDecision


def main() -> None:
    plan = OrchestrationPlan(
        id="orch_validation",
        request_id="wl_validation",
        action=OrchestrationAction.ROUTE,
        reason="validation route",
        created_at=datetime.now(timezone.utc),
        route_decision=RouteDecision(
            request_id="wl_validation",
            action=RouteAction.ROUTE,
            target_node="node.alpha",
            score=0.77,
            reason="validation target",
        ),
    )
    guard = PolicyGuard()
    dry = guard.evaluate_plan(plan, PolicyContext(subject="validator", dry_run=True))
    if dry.outcome != PolicyOutcome.ALLOW:
        raise SystemExit(f"dry-run should be allowed, got {dry.outcome}")

    live = guard.evaluate_plan(plan, PolicyContext(subject="validator", dry_run=False))
    if live.outcome != PolicyOutcome.REQUIRE_APPROVAL:
        raise SystemExit(f"live run should require approval, got {live.outcome}")
    if ApprovalToken.EXECUTE_LIVE.value not in live.required_approvals():
        raise SystemExit("missing execute.live approval requirement")

    approved = guard.evaluate_plan(
        plan,
        PolicyContext(subject="validator", dry_run=False, approvals=(ApprovalToken.EXECUTE_LIVE.value,)),
    )
    if approved.outcome != PolicyOutcome.ALLOW:
        raise SystemExit(f"approved live run should be allowed, got {approved.outcome}")

    print("OK: Policy & Governance MVP validation passed")


if __name__ == "__main__":
    main()
