"""CyberHIVE Policy & Governance MVP.

This module evaluates whether an orchestration plan, execution request or
exposure request is safe to proceed. It is intentionally local, deterministic
and dependency-free.

The MVP does not replace the lower-level safety checks in Inventory, Exposure
Gateway or Execution Engine. It sits above them and produces an auditable policy
decision before side effects are attempted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .exposure_gateway import ExposureRequest
from .integration_orchestrator import OrchestrationAction, OrchestrationPlan
from .inventory import ExposureMode, InventoryItem, Sensitivity


class PolicyOutcome(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class PolicySeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalToken(str, Enum):
    EXECUTE_LIVE = "execute.live"
    DATA_MOVE_EXECUTE = "data.move.execute"
    PREWARM_EXECUTE = "runtime.prewarm.execute"
    SECRET_PROCESS = "secret.process"
    PUBLIC_EXPOSURE = "exposure.public"
    RECORDING_ENABLE = "exposure.recording.enable"
    DOWNLOAD_ENABLE = "exposure.download.enable"
    OVERRIDE_REJECTED_ROUTE = "route.reject.override"


@dataclass(frozen=True)
class PolicyContext:
    """Information available to policy evaluation."""

    subject: str = "system"
    tenant: str | None = None
    dry_run: bool = True
    approvals: tuple[str, ...] = ()
    requested_permissions: tuple[str, ...] = ()
    environment: str = "local"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def has_approval(self, token: str | ApprovalToken) -> bool:
        value = token.value if isinstance(token, ApprovalToken) else token
        return value in self.approvals


@dataclass(frozen=True)
class PolicyFinding:
    rule_id: str
    outcome: PolicyOutcome
    severity: PolicySeverity
    reason: str
    required_approval: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "outcome": self.outcome.value,
            "severity": self.severity.value,
            "reason": self.reason,
            "required_approval": self.required_approval,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class PolicyDecision:
    id: str
    outcome: PolicyOutcome
    subject: str
    dry_run: bool
    created_at: datetime
    findings: tuple[PolicyFinding, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.outcome in {PolicyOutcome.ALLOW, PolicyOutcome.WARN}

    @property
    def requires_approval(self) -> bool:
        return self.outcome == PolicyOutcome.REQUIRE_APPROVAL

    def required_approvals(self) -> tuple[str, ...]:
        return tuple(
            sorted({finding.required_approval for finding in self.findings if finding.required_approval})
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "outcome": self.outcome.value,
            "subject": self.subject,
            "dry_run": self.dry_run,
            "created_at": self.created_at.isoformat(),
            "required_approvals": list(self.required_approvals()),
            "findings": [finding.as_dict() for finding in self.findings],
            "metadata": dict(self.metadata),
        }


class GovernanceJournal:
    """Append-only JSONL journal for policy decisions."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, decision: PolicyDecision) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(decision.as_dict(), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")

    def iter_decisions(self) -> tuple[dict[str, Any], ...]:
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return tuple(rows)

    def count(self) -> int:
        return len(self.iter_decisions())


class PolicyGuard:
    """Deterministic policy evaluator for the CyberHIVE MVP."""

    def __init__(self, *, journal: GovernanceJournal | None = None) -> None:
        self.journal = journal

    def evaluate_plan(self, plan: OrchestrationPlan, context: PolicyContext | None = None) -> PolicyDecision:
        ctx = context or PolicyContext()
        findings: list[PolicyFinding] = []

        if not plan.id:
            findings.append(_deny("plan.id.required", "orchestration plan id is required"))
        if not plan.request_id:
            findings.append(_deny("plan.request_id.required", "orchestration request id is required"))

        if ctx.dry_run:
            findings.append(
                PolicyFinding(
                    "dry_run.safe_default",
                    PolicyOutcome.ALLOW,
                    PolicySeverity.INFO,
                    "dry-run evaluation cannot trigger side effects",
                )
            )
        elif not ctx.has_approval(ApprovalToken.EXECUTE_LIVE):
            findings.append(
                _approval(
                    "live_execution.requires_approval",
                    "live execution requires explicit approval",
                    ApprovalToken.EXECUTE_LIVE,
                    severity=PolicySeverity.HIGH,
                )
            )

        if plan.action == OrchestrationAction.REJECT and not ctx.has_approval(ApprovalToken.OVERRIDE_REJECTED_ROUTE):
            findings.append(
                _deny(
                    "route.rejected",
                    "scheduler rejected the workload; execution cannot proceed without an explicit override",
                    severity=PolicySeverity.HIGH,
                    metadata={"plan_action": plan.action.value},
                )
            )

        if plan.action in {OrchestrationAction.ROUTE, OrchestrationAction.PREWARM}:
            if plan.route_decision is None or not plan.route_decision.target_node:
                findings.append(_deny("route.target.required", "routed plans require a target node", severity=PolicySeverity.HIGH))

        if plan.data_moves and not ctx.dry_run and not ctx.has_approval(ApprovalToken.DATA_MOVE_EXECUTE):
            findings.append(
                _approval(
                    "data_moves.require_approval",
                    "physical data moves require explicit approval before live execution",
                    ApprovalToken.DATA_MOVE_EXECUTE,
                    severity=PolicySeverity.HIGH,
                    metadata={"move_count": len(plan.data_moves)},
                )
            )

        if plan.prewarm and not ctx.dry_run and not ctx.has_approval(ApprovalToken.PREWARM_EXECUTE):
            findings.append(
                _approval(
                    "prewarm.requires_approval",
                    "prewarm side effects require explicit approval before live execution",
                    ApprovalToken.PREWARM_EXECUTE,
                    severity=PolicySeverity.MEDIUM,
                    metadata={"prewarm_count": len(plan.prewarm)},
                )
            )

        if _contains_secret_marker(plan.metadata) and not ctx.has_approval(ApprovalToken.SECRET_PROCESS):
            findings.append(
                _approval(
                    "secret.metadata.requires_approval",
                    "plan metadata includes secret sensitivity markers",
                    ApprovalToken.SECRET_PROCESS,
                    severity=PolicySeverity.CRITICAL,
                )
            )

        if plan.reuse_decision is not None and plan.action == OrchestrationAction.REUSE:
            findings.append(
                PolicyFinding(
                    "reuse.short_circuit.allowed",
                    PolicyOutcome.ALLOW,
                    PolicySeverity.LOW,
                    "cache reuse short-circuits compute execution",
                    metadata={"reuse_action": plan.reuse_decision.action.value},
                )
            )

        return self._finalize("plan", ctx, findings, metadata={"plan_id": plan.id, "plan_action": plan.action.value})

    def evaluate_exposure_request(
        self,
        request: ExposureRequest,
        item: InventoryItem,
        context: PolicyContext | None = None,
    ) -> PolicyDecision:
        ctx = context or PolicyContext()
        findings: list[PolicyFinding] = []

        if not item.enabled:
            findings.append(_deny("inventory.disabled", "disabled resources cannot be exposed"))
        if item.sensitivity == Sensitivity.SECRET:
            findings.append(_deny("exposure.secret.denied", "secret resources cannot be exposed through the MVP gateway"))
        if request.ttl_seconds > 24 * 3600:
            findings.append(_deny("exposure.ttl.max_24h", "exposure ttl exceeds the 24h MVP safety limit"))

        if request.requested_exposure == ExposureMode.PUBLIC:
            if item.sensitivity != Sensitivity.PUBLIC:
                findings.append(
                    _deny("exposure.public.sensitivity", "only public-sensitivity resources may request public exposure")
                )
            if not ctx.has_approval(ApprovalToken.PUBLIC_EXPOSURE):
                findings.append(
                    _approval(
                        "exposure.public.requires_approval",
                        "public exposure requires explicit approval",
                        ApprovalToken.PUBLIC_EXPOSURE,
                        severity=PolicySeverity.HIGH,
                    )
                )

        if request.allow_recording and not ctx.has_approval(ApprovalToken.RECORDING_ENABLE):
            findings.append(
                _approval(
                    "exposure.recording.requires_approval",
                    "recording must be explicitly approved",
                    ApprovalToken.RECORDING_ENABLE,
                    severity=PolicySeverity.HIGH,
                )
            )

        if request.allow_download and not ctx.has_approval(ApprovalToken.DOWNLOAD_ENABLE):
            findings.append(
                _approval(
                    "exposure.download.requires_approval",
                    "download must be explicitly approved",
                    ApprovalToken.DOWNLOAD_ENABLE,
                    severity=PolicySeverity.HIGH,
                )
            )

        for permission in request.permissions:
            if not item.supports_permission(permission):
                findings.append(
                    _deny(
                        "exposure.permission.unsupported",
                        f"resource does not support requested permission: {permission}",
                        metadata={"permission": permission},
                    )
                )

        return self._finalize(
            "exposure",
            ctx,
            findings,
            metadata={"resource_id": request.resource_id, "requested_exposure": request.requested_exposure.value},
        )

    def assert_allowed(self, decision: PolicyDecision) -> None:
        if not decision.allowed:
            required = ", ".join(decision.required_approvals()) or "none"
            raise PermissionError(f"policy decision is {decision.outcome.value}; required approvals: {required}")

    def _finalize(
        self,
        prefix: str,
        context: PolicyContext,
        findings: Iterable[PolicyFinding],
        *,
        metadata: Mapping[str, Any],
    ) -> PolicyDecision:
        items = tuple(findings)
        outcome = _worst_outcome(items)
        decision = PolicyDecision(
            id=f"pol_{prefix}_{int(datetime.now(timezone.utc).timestamp() * 1000000)}",
            outcome=outcome,
            subject=context.subject,
            dry_run=context.dry_run,
            created_at=datetime.now(timezone.utc),
            findings=items,
            metadata=dict(metadata),
        )
        if self.journal is not None:
            self.journal.append(decision)
        return decision


def _worst_outcome(findings: tuple[PolicyFinding, ...]) -> PolicyOutcome:
    if any(item.outcome == PolicyOutcome.DENY for item in findings):
        return PolicyOutcome.DENY
    if any(item.outcome == PolicyOutcome.REQUIRE_APPROVAL for item in findings):
        return PolicyOutcome.REQUIRE_APPROVAL
    if any(item.outcome == PolicyOutcome.WARN for item in findings):
        return PolicyOutcome.WARN
    return PolicyOutcome.ALLOW


def _deny(
    rule_id: str,
    reason: str,
    *,
    severity: PolicySeverity = PolicySeverity.CRITICAL,
    metadata: Mapping[str, Any] | None = None,
) -> PolicyFinding:
    return PolicyFinding(rule_id, PolicyOutcome.DENY, severity, reason, metadata=metadata or {})


def _approval(
    rule_id: str,
    reason: str,
    approval: ApprovalToken,
    *,
    severity: PolicySeverity,
    metadata: Mapping[str, Any] | None = None,
) -> PolicyFinding:
    return PolicyFinding(
        rule_id,
        PolicyOutcome.REQUIRE_APPROVAL,
        severity,
        reason,
        required_approval=approval.value,
        metadata=metadata or {},
    )


def _contains_secret_marker(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in {"sensitivity", "classification"} and str(nested).lower() == "secret":
                return True
            if _contains_secret_marker(nested):
                return True
    elif isinstance(value, (list, tuple, set)):
        return any(_contains_secret_marker(item) for item in value)
    return False
