"""CyberHIVE Execution Engine MVP.

Turns an Integration Orchestrator plan into an auditable execution run.

The MVP is intentionally conservative: it records and publishes lifecycle events,
but it does not run arbitrary commands, move files or call remote nodes by
default. Future handlers can be added behind explicit policy gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import uuid
from typing import Any, Mapping

from .hiveframe import Operation, OperationType
from .integration_orchestrator import OrchestrationAction, OrchestrationPlan, OrchestrationStep
from .runtime_bus import RuntimeBus


class ExecutionStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"


class ExecutionError(RuntimeError):
    """Raised when a plan cannot be safely executed by the MVP engine."""


@dataclass(frozen=True)
class ExecutionPolicy:
    """Safety gates for local MVP execution."""

    allow_physical_data_moves: bool = False
    allow_remote_execution: bool = False
    allow_prewarm_side_effects: bool = False
    require_dry_run_for_unknown_steps: bool = True


@dataclass(frozen=True)
class ExecutionStepResult:
    name: str
    status: ExecutionStatus
    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ExecutionRun:
    id: str
    plan_id: str
    request_id: str
    status: ExecutionStatus
    dry_run: bool
    started_at: datetime
    completed_at: datetime | None = None
    steps: tuple[ExecutionStepResult, ...] = ()
    events_published: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "dry_run": self.dry_run,
            "started_at": self.started_at.isoformat(),
            "completed_at": None if self.completed_at is None else self.completed_at.isoformat(),
            "steps": [step.as_dict() for step in self.steps],
            "events_published": self.events_published,
            "metadata": dict(self.metadata),
        }


class ExecutionJournal:
    """Append-only JSONL execution journal."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, run: ExecutionRun) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(run.as_dict(), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")

    def iter_runs(self) -> tuple[dict[str, Any], ...]:
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return tuple(rows)

    def count(self) -> int:
        return len(self.iter_runs())


class ExecutionEngine:
    """Safe local executor for orchestration plans."""

    def __init__(
        self,
        *,
        runtime_bus: RuntimeBus | None = None,
        journal: ExecutionJournal | None = None,
        policy: ExecutionPolicy | None = None,
    ) -> None:
        self.runtime_bus = runtime_bus
        self.journal = journal
        self.policy = policy or ExecutionPolicy()

    def execute(self, plan: OrchestrationPlan, *, dry_run: bool = True) -> ExecutionRun:
        self._validate_plan(plan)
        run_id = f"exec_{uuid.uuid4().hex[:20]}"
        started_at = datetime.now(timezone.utc)
        events = 0
        if self.runtime_bus is not None:
            self._publish(run_id, "execution.started", plan, {"dry_run": dry_run})
            events += 1

        try:
            step_results = tuple(self._execute_step(step, plan, dry_run=dry_run) for step in plan.steps)
            status = self._final_status(plan, step_results, dry_run=dry_run)
            completed_at = datetime.now(timezone.utc)
            run = ExecutionRun(
                id=run_id,
                plan_id=plan.id,
                request_id=plan.request_id,
                status=status,
                dry_run=dry_run,
                started_at=started_at,
                completed_at=completed_at,
                steps=step_results,
                events_published=events,
                metadata={"plan_action": plan.action.value, "plan_reason": plan.reason},
            )
            if self.runtime_bus is not None:
                self._publish(run_id, "execution.completed", plan, {"status": status.value})
                events += 1
                run = ExecutionRun(
                    id=run.id,
                    plan_id=run.plan_id,
                    request_id=run.request_id,
                    status=run.status,
                    dry_run=run.dry_run,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    steps=run.steps,
                    events_published=events,
                    metadata=run.metadata,
                )
            if self.journal is not None:
                self.journal.append(run)
            if self.runtime_bus is not None:
                self.runtime_bus.flush()
            return run
        except Exception as exc:  # noqa: BLE001 - convert to auditable failure
            completed_at = datetime.now(timezone.utc)
            failed = ExecutionRun(
                id=run_id,
                plan_id=plan.id,
                request_id=plan.request_id,
                status=ExecutionStatus.FAILED,
                dry_run=dry_run,
                started_at=started_at,
                completed_at=completed_at,
                steps=(ExecutionStepResult("execution", ExecutionStatus.FAILED, str(exc)),),
                events_published=events,
                metadata={"plan_action": plan.action.value, "error_type": type(exc).__name__},
            )
            if self.journal is not None:
                self.journal.append(failed)
            if isinstance(exc, ExecutionError):
                raise
            raise ExecutionError(str(exc)) from exc

    def _execute_step(self, step: OrchestrationStep, plan: OrchestrationPlan, *, dry_run: bool) -> ExecutionStepResult:
        if dry_run:
            return ExecutionStepResult(step.name, ExecutionStatus.DRY_RUN, f"dry-run: {step.reason}", step.metadata)

        if step.name == "reuse":
            if plan.action == OrchestrationAction.REUSE:
                return ExecutionStepResult(step.name, ExecutionStatus.SUCCEEDED, "reuse accepted; compute skipped", step.metadata)
            return ExecutionStepResult(step.name, ExecutionStatus.SKIPPED, "cache did not short-circuit execution", step.metadata)

        if step.name == "data_placement":
            return ExecutionStepResult(step.name, ExecutionStatus.SUCCEEDED, "placement decision accepted", step.metadata)

        if step.name == "data_moves":
            if not self.policy.allow_physical_data_moves:
                return ExecutionStepResult(step.name, ExecutionStatus.SKIPPED, "physical data moves disabled by execution policy", step.metadata)
            return ExecutionStepResult(step.name, ExecutionStatus.SUCCEEDED, "data move handler allowed by policy", step.metadata)

        if step.name == "scheduler_hints":
            return ExecutionStepResult(step.name, ExecutionStatus.SUCCEEDED, "scheduler hints applied to decision context", step.metadata)

        if step.name == "route":
            if plan.action == OrchestrationAction.REJECT:
                return ExecutionStepResult(step.name, ExecutionStatus.FAILED, "route rejected by scheduler", step.metadata)
            if plan.action == OrchestrationAction.QUEUE:
                return ExecutionStepResult(step.name, ExecutionStatus.SKIPPED, "workload queued instead of executed", step.metadata)
            return ExecutionStepResult(step.name, ExecutionStatus.SUCCEEDED, "route decision accepted", step.metadata)

        if step.name == "prewarm":
            if not self.policy.allow_prewarm_side_effects:
                return ExecutionStepResult(step.name, ExecutionStatus.SKIPPED, "prewarm side effects disabled by execution policy", step.metadata)
            return ExecutionStepResult(step.name, ExecutionStatus.SUCCEEDED, "prewarm handler allowed by policy", step.metadata)

        if self.policy.require_dry_run_for_unknown_steps:
            return ExecutionStepResult(step.name, ExecutionStatus.SKIPPED, "unknown step requires explicit handler", step.metadata)
        return ExecutionStepResult(step.name, ExecutionStatus.SUCCEEDED, "unknown step accepted by permissive policy", step.metadata)

    def _publish(self, run_id: str, event: str, plan: OrchestrationPlan, metadata: Mapping[str, Any]) -> None:
        if self.runtime_bus is None:
            return
        self.runtime_bus.publish(
            Operation.from_json_payload(
                OperationType.RESULT,
                f"execution.{run_id}.{event}",
                {
                    "event": event,
                    "run_id": run_id,
                    "plan_id": plan.id,
                    "request_id": plan.request_id,
                    "plan_action": plan.action.value,
                    "metadata": dict(metadata),
                },
                priority=80,
            )
        )

    def _validate_plan(self, plan: OrchestrationPlan) -> None:
        if not plan.id:
            raise ExecutionError("plan id is required")
        if not plan.request_id:
            raise ExecutionError("plan request_id is required")
        if plan.action == OrchestrationAction.REJECT and not plan.route_decision:
            raise ExecutionError("rejected plan must include route_decision")

    def _final_status(self, plan: OrchestrationPlan, steps: tuple[ExecutionStepResult, ...], *, dry_run: bool) -> ExecutionStatus:
        if dry_run:
            return ExecutionStatus.DRY_RUN
        if plan.action == OrchestrationAction.REJECT:
            return ExecutionStatus.FAILED
        if plan.action == OrchestrationAction.QUEUE:
            return ExecutionStatus.SKIPPED
        if any(step.status == ExecutionStatus.FAILED for step in steps):
            return ExecutionStatus.FAILED
        return ExecutionStatus.SUCCEEDED
