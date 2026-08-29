from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone

from cyberhive_core.data_fabric import DataMove, PlacementAction, StorageTier
from cyberhive_core.exposure_gateway import ExposureRequest
from cyberhive_core.integration_orchestrator import OrchestrationAction, OrchestrationPlan
from cyberhive_core.inventory import Capability, ExposureMode, InventoryItem, Sensitivity
from cyberhive_core.policy_governance import (
    ApprovalToken,
    GovernanceJournal,
    PolicyContext,
    PolicyGuard,
    PolicyOutcome,
)
from cyberhive_core.scheduler_router import RouteAction, RouteDecision


def _plan(**overrides):
    values = {
        "id": "orch_test",
        "request_id": "wl_test",
        "action": OrchestrationAction.ROUTE,
        "reason": "test plan",
        "created_at": datetime.now(timezone.utc),
        "route_decision": RouteDecision(
            request_id="wl_test",
            action=RouteAction.ROUTE,
            target_node="node.alpha",
            score=0.8,
            reason="healthy node",
        ),
    }
    values.update(overrides)
    return OrchestrationPlan(**values)


class PolicyGovernanceMvpTests(unittest.TestCase):
    def test_dry_run_plan_is_allowed(self) -> None:
        decision = PolicyGuard().evaluate_plan(_plan(), PolicyContext(subject="jan", dry_run=True))
        self.assertEqual(decision.outcome, PolicyOutcome.ALLOW)
        self.assertTrue(decision.allowed)

    def test_live_execution_requires_approval(self) -> None:
        decision = PolicyGuard().evaluate_plan(_plan(), PolicyContext(subject="jan", dry_run=False))
        self.assertEqual(decision.outcome, PolicyOutcome.REQUIRE_APPROVAL)
        self.assertIn(ApprovalToken.EXECUTE_LIVE.value, decision.required_approvals())

    def test_live_execution_with_approval_is_allowed(self) -> None:
        decision = PolicyGuard().evaluate_plan(
            _plan(),
            PolicyContext(subject="jan", dry_run=False, approvals=(ApprovalToken.EXECUTE_LIVE.value,)),
        )
        self.assertEqual(decision.outcome, PolicyOutcome.ALLOW)

    def test_data_moves_require_specific_approval(self) -> None:
        move = DataMove(
            object_id="dataset.current",
            action=PlacementAction.PROMOTE,
            from_tier=StorageTier.L4_HDD_RAID,
            to_tier=StorageTier.L2_LOCAL_NVME,
            replicas=1,
            target_devices=("nvme-a",),
            reason="hot data",
        )
        decision = PolicyGuard().evaluate_plan(
            _plan(data_moves=(move,)),
            PolicyContext(subject="jan", dry_run=False, approvals=(ApprovalToken.EXECUTE_LIVE.value,)),
        )
        self.assertEqual(decision.outcome, PolicyOutcome.REQUIRE_APPROVAL)
        self.assertIn(ApprovalToken.DATA_MOVE_EXECUTE.value, decision.required_approvals())

    def test_rejected_route_is_denied(self) -> None:
        decision = PolicyGuard().evaluate_plan(
            _plan(action=OrchestrationAction.REJECT, route_decision=None),
            PolicyContext(subject="jan", dry_run=True),
        )
        self.assertEqual(decision.outcome, PolicyOutcome.DENY)

    def test_secret_metadata_requires_approval(self) -> None:
        decision = PolicyGuard().evaluate_plan(
            _plan(metadata={"classification": "secret"}),
            PolicyContext(subject="jan", dry_run=True),
        )
        self.assertEqual(decision.outcome, PolicyOutcome.REQUIRE_APPROVAL)
        self.assertIn(ApprovalToken.SECRET_PROCESS.value, decision.required_approvals())

    def test_public_exposure_requires_approval(self) -> None:
        item = InventoryItem(
            id="site.status",
            kind="web",
            name="Status Page",
            sensitivity=Sensitivity.PUBLIC,
            exposure=ExposureMode.PUBLIC,
            capabilities=[Capability("web.read", ("read",))],
        )
        request = ExposureRequest(
            resource_id="site.status",
            subject="petr",
            permissions=("read",),
            requested_exposure=ExposureMode.PUBLIC,
        )
        decision = PolicyGuard().evaluate_exposure_request(request, item, PolicyContext(subject="jan"))
        self.assertEqual(decision.outcome, PolicyOutcome.REQUIRE_APPROVAL)
        self.assertIn(ApprovalToken.PUBLIC_EXPOSURE.value, decision.required_approvals())

    def test_secret_exposure_is_denied(self) -> None:
        item = InventoryItem(
            id="camera.secret",
            kind="camera",
            name="Secret Camera",
            sensitivity=Sensitivity.SECRET,
            exposure=ExposureMode.PRIVATE,
            capabilities=[Capability("video.stream", ("stream.read",))],
        )
        request = ExposureRequest(
            resource_id="camera.secret",
            subject="petr",
            permissions=("stream.read",),
            requested_exposure=ExposureMode.AUTHENTICATED,
        )
        decision = PolicyGuard().evaluate_exposure_request(request, item, PolicyContext(subject="jan"))
        self.assertEqual(decision.outcome, PolicyOutcome.DENY)

    def test_journal_records_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal = GovernanceJournal(f"{tmp}/governance.jsonl")
            guard = PolicyGuard(journal=journal)
            decision = guard.evaluate_plan(_plan(), PolicyContext(subject="jan"))
            self.assertEqual(journal.count(), 1)
            self.assertEqual(journal.iter_decisions()[0]["id"], decision.id)


if __name__ == "__main__":
    unittest.main()
