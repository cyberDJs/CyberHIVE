"""CyberHIVE Approval Workflow MVP.

Human-in-the-loop approval broker and governed execution controller.

This module closes the loop introduced by Policy & Governance:

* PolicyGuard says whether a plan is allowed, denied or needs approvals.
* ApprovalBroker creates auditable approval requests and grants tokens.
* GovernedExecutionController evaluates policy before handing a plan to the
  ExecutionEngine.

The MVP is intentionally local and deterministic. It does not send messages,
open tickets or grant long-lived privileges. Approvals are scoped to a single
policy decision and expire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
from pathlib import Path
import uuid
from typing import Any, Iterable, Mapping

from .execution_engine import ExecutionEngine, ExecutionPolicy, ExecutionRun
from .integration_orchestrator import OrchestrationPlan
from .policy_governance import ApprovalToken, PolicyContext, PolicyDecision, PolicyGuard, PolicyOutcome


class ApprovalStatus(str, Enum):
    OPEN = "open"
    PARTIALLY_APPROVED = "partially_approved"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class GovernedExecutionOutcome(str, Enum):
    DRY_RUN = "dry_run"
    EXECUTED = "executed"
    APPROVAL_REQUIRED = "approval_required"
    DENIED = "denied"


class ApprovalError(RuntimeError):
    """Raised when an approval request cannot be created or modified."""


@dataclass(frozen=True)
class ApprovalGrant:
    approver: str
    tokens: tuple[str, ...]
    reason: str
    created_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "approver": self.approver,
            "tokens": list(self.tokens),
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    policy_decision_id: str
    subject: str
    requested_by: str
    required_tokens: tuple[str, ...]
    created_at: datetime
    expires_at: datetime
    status: ApprovalStatus = ApprovalStatus.OPEN
    granted_tokens: tuple[str, ...] = ()
    grants: tuple[ApprovalGrant, ...] = ()
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def missing_tokens(self) -> tuple[str, ...]:
        granted = set(self.granted_tokens)
        return tuple(token for token in self.required_tokens if token not in granted)

    def is_expired(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        return current >= self.expires_at

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "policy_decision_id": self.policy_decision_id,
            "subject": self.subject,
            "requested_by": self.requested_by,
            "required_tokens": list(self.required_tokens),
            "granted_tokens": list(self.granted_tokens),
            "missing_tokens": list(self.missing_tokens()),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "reason": self.reason,
            "grants": [grant.as_dict() for grant in self.grants],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class GovernedExecutionResult:
    id: str
    outcome: GovernedExecutionOutcome
    decision: PolicyDecision
    created_at: datetime
    reason: str
    approval_request: ApprovalRequest | None = None
    run: ExecutionRun | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "outcome": self.outcome.value,
            "decision": self.decision.as_dict(),
            "created_at": self.created_at.isoformat(),
            "reason": self.reason,
            "approval_request": None if self.approval_request is None else self.approval_request.as_dict(),
            "run": None if self.run is None else self.run.as_dict(),
            "metadata": dict(self.metadata),
        }


class ApprovalJournal:
    """Append-only JSONL journal for approval workflow events."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, event_type: str, payload: Mapping[str, Any]) -> None:
        row = {
            "event_type": event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "payload": dict(payload),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")

    def iter_events(self) -> tuple[dict[str, Any], ...]:
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return tuple(rows)

    def count(self) -> int:
        return len(self.iter_events())


class ApprovalBroker:
    """In-memory approval request broker with optional JSONL journaling."""

    def __init__(self, *, journal: ApprovalJournal | None = None) -> None:
        self.journal = journal
        self._requests: dict[str, ApprovalRequest] = {}

    def create_request(
        self,
        decision: PolicyDecision,
        *,
        requested_by: str,
        ttl_seconds: int = 900,
        reason: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> ApprovalRequest:
        if decision.outcome != PolicyOutcome.REQUIRE_APPROVAL:
            raise ApprovalError("approval request can only be created for require_approval decisions")
        if ttl_seconds <= 0:
            raise ApprovalError("approval ttl must be positive")
        required = decision.required_approvals()
        if not required:
            raise ApprovalError("policy decision has no approval tokens")

        now = datetime.now(timezone.utc)
        request = ApprovalRequest(
            id=f"appr_{uuid.uuid4().hex[:20]}",
            policy_decision_id=decision.id,
            subject=decision.subject,
            requested_by=requested_by,
            required_tokens=required,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            reason=reason,
            metadata=metadata or {},
        )
        self._requests[request.id] = request
        self._journal("approval.created", request.as_dict())
        return request

    def approve(
        self,
        request_id: str,
        *,
        approver: str,
        tokens: Iterable[str | ApprovalToken] | None = None,
        reason: str = "",
    ) -> ApprovalRequest:
        request = self._get_mutable(request_id)
        wanted = _normalize_tokens(tokens if tokens is not None else request.missing_tokens())
        if not wanted:
            raise ApprovalError("approval token list is empty")

        invalid = tuple(token for token in wanted if token not in request.required_tokens)
        if invalid:
            raise ApprovalError(f"approval includes tokens not required by request: {', '.join(invalid)}")

        now = datetime.now(timezone.utc)
        grant = ApprovalGrant(approver=approver, tokens=wanted, reason=reason, created_at=now)
        granted = tuple(sorted(set(request.granted_tokens).union(wanted)))
        status = ApprovalStatus.APPROVED if set(request.required_tokens).issubset(granted) else ApprovalStatus.PARTIALLY_APPROVED
        updated = _replace_request(request, status=status, granted_tokens=granted, grants=request.grants + (grant,))
        self._requests[request_id] = updated
        self._journal("approval.approved", updated.as_dict())
        return updated

    def deny(self, request_id: str, *, approver: str, reason: str) -> ApprovalRequest:
        request = self._get_mutable(request_id)
        grant = ApprovalGrant(approver=approver, tokens=(), reason=reason, created_at=datetime.now(timezone.utc))
        updated = _replace_request(request, status=ApprovalStatus.DENIED, grants=request.grants + (grant,))
        self._requests[request_id] = updated
        self._journal("approval.denied", updated.as_dict())
        return updated

    def cancel(self, request_id: str, *, reason: str = "") -> ApprovalRequest:
        request = self._get_mutable(request_id)
        updated = _replace_request(request, status=ApprovalStatus.CANCELLED, reason=reason or request.reason)
        self._requests[request_id] = updated
        self._journal("approval.cancelled", updated.as_dict())
        return updated

    def get(self, request_id: str) -> ApprovalRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise ApprovalError(f"approval request not found: {request_id}")
        return self._refresh_expiry(request)

    def list_open(self) -> tuple[ApprovalRequest, ...]:
        return tuple(
            request
            for request in (self._refresh_expiry(item) for item in self._requests.values())
            if request.status in {ApprovalStatus.OPEN, ApprovalStatus.PARTIALLY_APPROVED}
        )

    def context_with_approvals(self, base: PolicyContext, request_id: str) -> PolicyContext:
        request = self.get(request_id)
        if request.status != ApprovalStatus.APPROVED:
            raise ApprovalError(f"approval request is not approved: {request.status.value}")
        approvals = tuple(sorted(set(base.approvals).union(request.granted_tokens)))
        return PolicyContext(
            subject=base.subject,
            tenant=base.tenant,
            dry_run=base.dry_run,
            approvals=approvals,
            requested_permissions=base.requested_permissions,
            environment=base.environment,
            metadata={**dict(base.metadata), "approval_request_id": request.id},
        )

    def _get_mutable(self, request_id: str) -> ApprovalRequest:
        request = self.get(request_id)
        if request.status in {ApprovalStatus.APPROVED, ApprovalStatus.DENIED, ApprovalStatus.EXPIRED, ApprovalStatus.CANCELLED}:
            raise ApprovalError(f"approval request is closed: {request.status.value}")
        return request

    def _refresh_expiry(self, request: ApprovalRequest) -> ApprovalRequest:
        if request.status in {ApprovalStatus.OPEN, ApprovalStatus.PARTIALLY_APPROVED} and request.is_expired():
            updated = _replace_request(request, status=ApprovalStatus.EXPIRED)
            self._requests[request.id] = updated
            self._journal("approval.expired", updated.as_dict())
            return updated
        return request

    def _journal(self, event_type: str, payload: Mapping[str, Any]) -> None:
        if self.journal is not None:
            self.journal.append(event_type, payload)


class GovernedExecutionController:
    """Policy-aware wrapper around ExecutionEngine."""

    def __init__(
        self,
        *,
        policy_guard: PolicyGuard | None = None,
        approval_broker: ApprovalBroker | None = None,
        execution_engine: ExecutionEngine | None = None,
    ) -> None:
        self.policy_guard = policy_guard or PolicyGuard()
        self.approval_broker = approval_broker or ApprovalBroker()
        self.execution_engine = execution_engine

    def evaluate_or_execute(
        self,
        plan: OrchestrationPlan,
        *,
        context: PolicyContext | None = None,
        requested_by: str | None = None,
        approval_ttl_seconds: int = 900,
    ) -> GovernedExecutionResult:
        ctx = context or PolicyContext()
        decision = self.policy_guard.evaluate_plan(plan, ctx)

        if decision.outcome == PolicyOutcome.DENY:
            return _governed_result(
                GovernedExecutionOutcome.DENIED,
                decision,
                reason="policy denied execution",
                metadata={"plan_id": plan.id},
            )

        if decision.outcome == PolicyOutcome.REQUIRE_APPROVAL:
            approval = self.approval_broker.create_request(
                decision,
                requested_by=requested_by or ctx.subject,
                ttl_seconds=approval_ttl_seconds,
                reason="policy approval required before execution",
                metadata={"plan_id": plan.id, "request_id": plan.request_id},
            )
            return _governed_result(
                GovernedExecutionOutcome.APPROVAL_REQUIRED,
                decision,
                approval_request=approval,
                reason="approval request created",
                metadata={"required_approvals": decision.required_approvals()},
            )

        engine = self._engine_for_context(ctx)
        run = engine.execute(plan, dry_run=ctx.dry_run)
        return _governed_result(
            GovernedExecutionOutcome.DRY_RUN if ctx.dry_run else GovernedExecutionOutcome.EXECUTED,
            decision,
            run=run,
            reason="policy allowed execution",
            metadata={"run_status": run.status.value},
        )

    def resume_with_approval(
        self,
        plan: OrchestrationPlan,
        *,
        approval_request_id: str,
        context: PolicyContext | None = None,
    ) -> GovernedExecutionResult:
        base = context or PolicyContext(dry_run=False)
        approved_context = self.approval_broker.context_with_approvals(base, approval_request_id)
        return self.evaluate_or_execute(plan, context=approved_context, requested_by=approved_context.subject)

    def _engine_for_context(self, context: PolicyContext) -> ExecutionEngine:
        if self.execution_engine is not None:
            return self.execution_engine
        return ExecutionEngine(
            policy=ExecutionPolicy(
                allow_physical_data_moves=context.has_approval(ApprovalToken.DATA_MOVE_EXECUTE),
                allow_prewarm_side_effects=context.has_approval(ApprovalToken.PREWARM_EXECUTE),
            )
        )


def _governed_result(
    outcome: GovernedExecutionOutcome,
    decision: PolicyDecision,
    *,
    reason: str,
    approval_request: ApprovalRequest | None = None,
    run: ExecutionRun | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> GovernedExecutionResult:
    return GovernedExecutionResult(
        id=f"govexec_{uuid.uuid4().hex[:20]}",
        outcome=outcome,
        decision=decision,
        created_at=datetime.now(timezone.utc),
        reason=reason,
        approval_request=approval_request,
        run=run,
        metadata=metadata or {},
    )


def _normalize_tokens(tokens: Iterable[str | ApprovalToken]) -> tuple[str, ...]:
    values = []
    for token in tokens:
        values.append(token.value if isinstance(token, ApprovalToken) else str(token))
    return tuple(sorted(set(values)))


def _replace_request(
    request: ApprovalRequest,
    *,
    status: ApprovalStatus | None = None,
    granted_tokens: tuple[str, ...] | None = None,
    grants: tuple[ApprovalGrant, ...] | None = None,
    reason: str | None = None,
) -> ApprovalRequest:
    return ApprovalRequest(
        id=request.id,
        policy_decision_id=request.policy_decision_id,
        subject=request.subject,
        requested_by=request.requested_by,
        required_tokens=request.required_tokens,
        created_at=request.created_at,
        expires_at=request.expires_at,
        status=status if status is not None else request.status,
        granted_tokens=granted_tokens if granted_tokens is not None else request.granted_tokens,
        grants=grants if grants is not None else request.grants,
        reason=reason if reason is not None else request.reason,
        metadata=request.metadata,
    )
