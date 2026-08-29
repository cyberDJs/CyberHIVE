#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.approval_workflow import ApprovalBroker, ApprovalStatus, GovernedExecutionController, GovernedExecutionOutcome
from cyberhive_core.integration_orchestrator import OrchestrationAction, OrchestrationPlan
from cyberhive_core.policy_governance import ApprovalToken, PolicyContext, PolicyGuard, PolicyOutcome
from cyberhive_core.scheduler_router import RouteAction, RouteDecision
from datetime import datetime, timezone


def main() -> None:
    plan = OrchestrationPlan(
        id="orch_validation",
        request_id="wl_validation",
        action=OrchestrationAction.ROUTE,
        reason="validation plan",
        created_at=datetime.now(timezone.utc),
        route_decision=RouteDecision(
            request_id="wl_validation",
            action=RouteAction.ROUTE,
            target_node="node.beta",
            score=0.8,
            reason="healthy node",
        ),
    )
    guard = PolicyGuard()
    decision = guard.evaluate_plan(plan, PolicyContext(subject="validator", dry_run=False))
    assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL
    broker = ApprovalBroker()
    approval = broker.create_request(decision, requested_by="validator")
    assert approval.status == ApprovalStatus.OPEN
    approval = broker.approve(approval.id, approver="validator", tokens=(ApprovalToken.EXECUTE_LIVE,))
    assert approval.status == ApprovalStatus.APPROVED

    controller = GovernedExecutionController(policy_guard=guard, approval_broker=broker)
    result = controller.resume_with_approval(
        plan,
        approval_request_id=approval.id,
        context=PolicyContext(subject="validator", dry_run=False),
    )
    assert result.outcome == GovernedExecutionOutcome.EXECUTED
    assert result.run is not None
    print("OK: Approval Workflow MVP validation passed")


if __name__ == "__main__":
    main()
