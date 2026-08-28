"""CyberHIVE Integration Orchestrator MVP.

This module wires the previously separate MVP layers into one explainable plan:

* Cache & Reuse Fabric answers: can we avoid execution entirely?
* Data Fabric answers: where should required data live?
* Observations/Forecasting answers: what scheduler hints should affect routing?
* Scheduler/Router answers: where should work run?
* Prewarm Planner answers: what preparation should happen before execution?

The MVP still does not execute workloads. It produces an auditable orchestration
plan that is safe to inspect, test and later hand off to an executor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Any, Iterable, Mapping

from .cache_reuse import CanonicalOperation, ExecutionCost, ReuseAction, ReuseDecision, ReuseEngine
from .data_fabric import DataFabric, DataMove, PlacementDecision
from .observations_forecasting import SchedulerHint as ForecastSchedulerHint
from .observations_forecasting import SchedulerHintAction
from .scheduler_router import (
    ComputeRouter,
    HintAction,
    NodeState,
    PrewarmPlan,
    PrewarmPlanner,
    RouteAction,
    RouteDecision,
    SchedulerHintImpact,
    WorkloadRequest,
)


class OrchestrationAction(str, Enum):
    REUSE = "reuse"
    ROUTE = "route"
    PREWARM = "prewarm"
    QUEUE = "queue"
    REJECT = "reject"


@dataclass(frozen=True)
class OrchestrationRequest:
    """A single high-level request entering CyberHIVE Core.

    The request deliberately carries both the canonical operation used for cache
    reuse and the workload used for compute routing. That keeps the decision
    explainable: cache hit can short-circuit execution; cache miss continues into
    placement and scheduling.
    """

    operation: CanonicalOperation
    workload: WorkloadRequest
    data_object_ids: tuple[str, ...] = ()
    scheduler_hints: tuple[SchedulerHintImpact | ForecastSchedulerHint | Mapping[str, Any], ...] = ()
    subject: str | None = None
    recompute_cost: ExecutionCost = field(default_factory=ExecutionCost)
    freshness_tolerance_seconds: int = 0
    allow_reuse: bool = True
    plan_data_moves: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OrchestrationStep:
    name: str
    status: str
    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class OrchestrationPlan:
    id: str
    request_id: str
    action: OrchestrationAction
    reason: str
    created_at: datetime
    reuse_decision: ReuseDecision | None = None
    route_decision: RouteDecision | None = None
    scheduler_hints: tuple[SchedulerHintImpact, ...] = ()
    placement: Mapping[str, PlacementDecision] = field(default_factory=dict)
    data_moves: tuple[DataMove, ...] = ()
    prewarm: tuple[PrewarmPlan, ...] = ()
    steps: tuple[OrchestrationStep, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "action": self.action.value,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "reuse_decision": None
            if self.reuse_decision is None
            else {
                "action": self.reuse_decision.action.value,
                "cache_key": self.reuse_decision.cache_key,
                "reason": self.reuse_decision.reason,
                "confidence": self.reuse_decision.confidence,
                "estimated_saved_score": self.reuse_decision.estimated_saved_score,
                "pattern_id": self.reuse_decision.pattern_id,
            },
            "route_decision": None if self.route_decision is None else self.route_decision.as_dict(),
            "scheduler_hints": [
                {
                    "action": hint.action.value,
                    "target": hint.target,
                    "priority": hint.priority,
                    "reason": hint.reason,
                    "metadata": dict(hint.metadata),
                }
                for hint in self.scheduler_hints
            ],
            "placement": {
                object_id: {
                    "tier": decision.tier.value,
                    "temperature": decision.temperature,
                    "replicas": decision.replicas,
                    "action": decision.action.value,
                    "target_devices": list(decision.target_devices),
                    "score": decision.score,
                    "reason": decision.reason,
                }
                for object_id, decision in self.placement.items()
            },
            "data_moves": [
                {
                    "object_id": move.object_id,
                    "action": move.action.value,
                    "from_tier": None if move.from_tier is None else move.from_tier.value,
                    "to_tier": move.to_tier.value,
                    "replicas": move.replicas,
                    "target_devices": list(move.target_devices),
                    "reason": move.reason,
                }
                for move in self.data_moves
            ],
            "prewarm": [plan.as_dict() for plan in self.prewarm],
            "steps": [step.as_dict() for step in self.steps],
            "metadata": dict(self.metadata),
        }


class IntegrationOrchestrator:
    """Coordinates reuse, placement, routing and prewarm decisions."""

    def __init__(
        self,
        *,
        reuse_engine: ReuseEngine | None = None,
        data_fabric: DataFabric | None = None,
        router: ComputeRouter | None = None,
        prewarm_planner: PrewarmPlanner | None = None,
    ) -> None:
        self.reuse_engine = reuse_engine or ReuseEngine()
        self.data_fabric = data_fabric or DataFabric()
        self.router = router or ComputeRouter()
        self.prewarm_planner = prewarm_planner or PrewarmPlanner()

    def orchestrate(self, request: OrchestrationRequest) -> OrchestrationPlan:
        self._validate_request(request)
        plan_id = f"orch_{uuid.uuid4().hex[:20]}"
        steps: list[OrchestrationStep] = []
        placement: dict[str, PlacementDecision] = {}
        data_moves: tuple[DataMove, ...] = ()

        reuse_decision: ReuseDecision | None = None
        if request.allow_reuse:
            reuse_decision = self.reuse_engine.resolve_operation(
                request.operation,
                recompute_cost=request.recompute_cost,
                subject=request.subject,
                freshness_tolerance_seconds=request.freshness_tolerance_seconds,
            )
            steps.append(
                OrchestrationStep(
                    name="reuse",
                    status=reuse_decision.action.value,
                    reason=reuse_decision.reason,
                    metadata={"saved_score": reuse_decision.estimated_saved_score},
                )
            )
            if reuse_decision.action == ReuseAction.REUSE_EXACT:
                return OrchestrationPlan(
                    id=plan_id,
                    request_id=request.workload.id,
                    action=OrchestrationAction.REUSE,
                    reason="exact cache hit; execution skipped",
                    created_at=datetime.now(timezone.utc),
                    reuse_decision=reuse_decision,
                    steps=tuple(steps),
                    metadata=dict(request.metadata),
                )
        else:
            steps.append(OrchestrationStep(name="reuse", status="skipped", reason="reuse disabled for request"))

        if request.data_object_ids:
            for object_id in request.data_object_ids:
                decision = self.data_fabric.decide(object_id)
                placement[object_id] = decision
            steps.append(
                OrchestrationStep(
                    name="data_placement",
                    status="planned",
                    reason=f"placement evaluated for {len(placement)} object(s)",
                    metadata={object_id: decision.action.value for object_id, decision in placement.items()},
                )
            )
            if request.plan_data_moves:
                wanted = set(request.data_object_ids)
                data_moves = tuple(move for move in self.data_fabric.migration_plan() if move.object_id in wanted)
                steps.append(
                    OrchestrationStep(
                        name="data_moves",
                        status="planned" if data_moves else "none",
                        reason=f"{len(data_moves)} migration candidate(s)",
                    )
                )

        scheduler_hints = tuple(_coerce_orchestration_hint(hint, request.workload) for hint in request.scheduler_hints)
        self.router.set_hints(scheduler_hints)
        steps.append(
            OrchestrationStep(
                name="scheduler_hints",
                status="loaded" if scheduler_hints else "none",
                reason=f"{len(scheduler_hints)} hint(s) applied to router",
            )
        )

        route_decision = self.router.route(request.workload)
        steps.append(
            OrchestrationStep(
                name="route",
                status=route_decision.action.value,
                reason=route_decision.reason,
                metadata={"target_node": route_decision.target_node, "score": route_decision.score},
            )
        )

        prewarm = self.prewarm_planner.build_plans(
            hints=scheduler_hints,
            workloads=(request.workload,),
            nodes=_router_nodes(self.router),
        )
        if prewarm:
            steps.append(
                OrchestrationStep(
                    name="prewarm",
                    status="planned",
                    reason=f"{len(prewarm)} prewarm plan(s)",
                    metadata={plan.target_node: plan.model_id for plan in prewarm},
                )
            )

        action = _action_from_route(route_decision)
        if prewarm and action == OrchestrationAction.ROUTE and route_decision.action == RouteAction.PREWARM:
            action = OrchestrationAction.PREWARM

        return OrchestrationPlan(
            id=plan_id,
            request_id=request.workload.id,
            action=action,
            reason=_plan_reason(reuse_decision=reuse_decision, route_decision=route_decision, prewarm=prewarm),
            created_at=datetime.now(timezone.utc),
            reuse_decision=reuse_decision,
            route_decision=route_decision,
            scheduler_hints=scheduler_hints,
            placement=placement,
            data_moves=data_moves,
            prewarm=prewarm,
            steps=tuple(steps),
            metadata=dict(request.metadata),
        )

    def _validate_request(self, request: OrchestrationRequest) -> None:
        if not request.operation.operation:
            raise ValueError("operation.operation is required")
        if request.freshness_tolerance_seconds < 0:
            raise ValueError("freshness_tolerance_seconds must not be negative")


def _coerce_orchestration_hint(
    hint: SchedulerHintImpact | ForecastSchedulerHint | Mapping[str, Any],
    workload: WorkloadRequest,
) -> SchedulerHintImpact:
    if isinstance(hint, SchedulerHintImpact):
        return hint
    if isinstance(hint, ForecastSchedulerHint):
        metadata = dict(hint.metadata)
        if hint.action == SchedulerHintAction.PREWARM and workload.model_id and "model_id" not in metadata:
            metadata["model_id"] = workload.model_id
        return SchedulerHintImpact(
            action=HintAction(hint.action.value),
            target=hint.target,
            priority=hint.priority,
            reason=hint.reason,
            metadata=metadata,
        )
    action = HintAction(str(hint.get("action")))
    metadata = dict(hint.get("metadata", {}) or {})
    if action == HintAction.PREWARM and workload.model_id and "model_id" not in metadata:
        metadata["model_id"] = workload.model_id
    return SchedulerHintImpact(
        action=action,
        target=str(hint.get("target")),
        priority=int(hint.get("priority", 0)),
        reason=str(hint.get("reason", "")),
        metadata=metadata,
    )


def _router_nodes(router: ComputeRouter) -> tuple[NodeState, ...]:
    # The router owns node scoring state in the MVP. A public accessor can be
    # introduced later; until then, keep this private access contained here.
    return tuple(getattr(router, "_nodes", {}).values())


def _action_from_route(route: RouteDecision) -> OrchestrationAction:
    if route.action == RouteAction.REJECT:
        return OrchestrationAction.REJECT
    if route.action == RouteAction.QUEUE:
        return OrchestrationAction.QUEUE
    if route.action == RouteAction.PREWARM:
        return OrchestrationAction.PREWARM
    return OrchestrationAction.ROUTE


def _plan_reason(*, reuse_decision: ReuseDecision | None, route_decision: RouteDecision, prewarm: tuple[PrewarmPlan, ...]) -> str:
    parts: list[str] = []
    if reuse_decision is not None:
        parts.append(f"reuse={reuse_decision.action.value}")
    parts.append(f"route={route_decision.action.value}")
    if route_decision.target_node:
        parts.append(f"target={route_decision.target_node}")
    if prewarm:
        parts.append(f"prewarm={len(prewarm)}")
    return "; ".join(parts)
