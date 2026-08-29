"""CyberHIVE Scheduler and Router MVP.

This module turns scheduler hints and node state into route decisions. The MVP is
small, local and dependency-free. It does not execute workloads. It decides where
work should go, why, and which preparatory actions should happen first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
import uuid
from typing import Any, Iterable, Mapping, Sequence


class WorkloadKind(str, Enum):
    INTERACTIVE_INFERENCE = "interactive_inference"
    BATCH_INFERENCE = "batch_inference"
    DATA_MOVE = "data_move"
    INDEXING = "indexing"
    BUILD = "build"
    ENCODING = "encoding"
    MAINTENANCE = "maintenance"


class WorkloadPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class RouteAction(str, Enum):
    ROUTE = "route"
    QUEUE = "queue"
    REJECT = "reject"
    PREWARM = "prewarm"


class HintAction(str, Enum):
    PREWARM = "prewarm"
    SHIFT_LOAD = "shift_load"
    THROTTLE_BACKGROUND = "throttle_background"
    HOLD_CAPACITY = "hold_capacity"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"


@dataclass(frozen=True)
class NodeState:
    """Current schedulable capacity and routing state for a node."""

    id: str
    enabled: bool = True
    healthy: bool = True
    capabilities: tuple[str, ...] = ()
    labels: Mapping[str, str] = field(default_factory=dict)
    cpu_cores: float = 0.0
    free_cpu_cores: float = 0.0
    memory_gb: float = 0.0
    free_memory_gb: float = 0.0
    gpu_vram_gb: float = 0.0
    free_vram_gb: float = 0.0
    gpu_utilization: float = 0.0
    queue_depth: int = 0
    latency_ms: float = 0.0
    data_locality: tuple[str, ...] = ()
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def supports(self, workload: "WorkloadRequest") -> bool:
        required = set(workload.required_capabilities)
        return required.issubset(set(self.capabilities))


@dataclass(frozen=True)
class WorkloadRequest:
    """A unit of work that needs a target node."""

    kind: WorkloadKind
    required_capabilities: tuple[str, ...] = ()
    id: str = field(default_factory=lambda: f"wl_{uuid.uuid4().hex[:20]}")
    priority: WorkloadPriority = WorkloadPriority.NORMAL
    estimated_cpu_cores: float = 0.0
    estimated_memory_gb: float = 0.0
    estimated_vram_gb: float = 0.0
    latency_sensitive: bool = False
    interactive: bool = False
    model_id: str | None = None
    data_affinity: tuple[str, ...] = ()
    avoid_nodes: tuple[str, ...] = ()
    prefer_nodes: tuple[str, ...] = ()
    labels_required: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SchedulerHintImpact:
    action: HintAction
    target: str
    priority: int
    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NodeScore:
    node_id: str
    score: float
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RouteDecision:
    request_id: str
    action: RouteAction
    target_node: str | None
    score: float
    reason: str
    alternatives: tuple[NodeScore, ...] = ()
    prewarm: tuple[str, ...] = ()
    queue: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action": self.action.value,
            "target_node": self.target_node,
            "score": self.score,
            "reason": self.reason,
            "alternatives": [
                {
                    "node_id": item.node_id,
                    "score": item.score,
                    "eligible": item.eligible,
                    "reasons": list(item.reasons),
                }
                for item in self.alternatives
            ],
            "prewarm": list(self.prewarm),
            "queue": self.queue,
        }


@dataclass(frozen=True)
class PrewarmPlan:
    id: str
    target_node: str
    model_id: str
    reason: str
    priority: int
    actions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_node": self.target_node,
            "model_id": self.model_id,
            "reason": self.reason,
            "priority": self.priority,
            "actions": list(self.actions),
        }


class ComputeRouter:
    """Scores nodes and returns deterministic routing decisions."""

    def __init__(self, *, minimum_interactive_vram_headroom_gb: float = 0.5) -> None:
        self.minimum_interactive_vram_headroom_gb = minimum_interactive_vram_headroom_gb
        self._nodes: dict[str, NodeState] = {}
        self._hints: list[SchedulerHintImpact] = []

    def upsert_node(self, node: NodeState) -> None:
        _validate_node(node)
        self._nodes[node.id] = node

    def set_hints(self, hints: Iterable[SchedulerHintImpact | Mapping[str, Any]]) -> None:
        self._hints = [_coerce_hint(hint) for hint in hints]

    def route(self, request: WorkloadRequest) -> RouteDecision:
        _validate_workload(request)
        scores = tuple(self._score_node(node, request) for node in self._nodes.values())
        eligible = sorted((item for item in scores if item.eligible), key=lambda item: item.score, reverse=True)

        if not eligible:
            reason = "no eligible node; " + _join_reasons(scores)
            return RouteDecision(
                request_id=request.id,
                action=RouteAction.REJECT,
                target_node=None,
                score=0.0,
                reason=reason,
                alternatives=scores,
                queue=request.priority in {WorkloadPriority.LOW, WorkloadPriority.NORMAL},
            )

        best = eligible[0]
        selected_hints = [hint for hint in self._hints if hint.target == best.node_id]
        prewarm_models = tuple(
            str(hint.metadata.get("model_id"))
            for hint in selected_hints
            if hint.action == HintAction.PREWARM and hint.metadata.get("model_id")
        )

        if best.score < 0.25 and request.priority != WorkloadPriority.CRITICAL:
            return RouteDecision(
                request_id=request.id,
                action=RouteAction.QUEUE,
                target_node=best.node_id,
                score=best.score,
                reason="best node is eligible but pressure is too high for immediate execution",
                alternatives=scores,
                prewarm=prewarm_models,
                queue=True,
            )

        action = RouteAction.PREWARM if prewarm_models and request.model_id in prewarm_models else RouteAction.ROUTE
        return RouteDecision(
            request_id=request.id,
            action=action,
            target_node=best.node_id,
            score=best.score,
            reason="; ".join(best.reasons),
            alternatives=scores,
            prewarm=prewarm_models,
            queue=False,
        )

    def _score_node(self, node: NodeState, request: WorkloadRequest) -> NodeScore:
        reasons: list[str] = []
        if not node.enabled:
            return NodeScore(node.id, 0.0, False, ("node disabled",))
        if not node.healthy:
            return NodeScore(node.id, 0.0, False, ("node unhealthy",))
        if node.id in request.avoid_nodes:
            return NodeScore(node.id, 0.0, False, ("node explicitly avoided",))
        if not node.supports(request):
            return NodeScore(node.id, 0.0, False, ("missing required capability",))
        for key, value in request.labels_required.items():
            if node.labels.get(key) != value:
                return NodeScore(node.id, 0.0, False, (f"missing label {key}={value}",))
        if request.estimated_cpu_cores > node.free_cpu_cores:
            return NodeScore(node.id, 0.0, False, ("insufficient CPU headroom",))
        if request.estimated_memory_gb > node.free_memory_gb:
            return NodeScore(node.id, 0.0, False, ("insufficient memory headroom",))
        if request.estimated_vram_gb > node.free_vram_gb:
            return NodeScore(node.id, 0.0, False, ("insufficient VRAM headroom",))

        free_vram_after = node.free_vram_gb - request.estimated_vram_gb
        if request.interactive and free_vram_after < self.minimum_interactive_vram_headroom_gb:
            return NodeScore(node.id, 0.0, False, ("interactive VRAM reserve would be violated",))

        score = 0.0
        score += _ratio(node.free_cpu_cores, max(node.cpu_cores, request.estimated_cpu_cores, 1.0)) * 0.18
        score += _ratio(node.free_memory_gb, max(node.memory_gb, request.estimated_memory_gb, 1.0)) * 0.16
        score += _ratio(node.free_vram_gb, max(node.gpu_vram_gb, request.estimated_vram_gb, 1.0)) * 0.24
        score += max(0.0, 1.0 - min(1.0, node.gpu_utilization)) * 0.16
        score += max(0.0, 1.0 - min(1.0, node.queue_depth / 10.0)) * 0.12
        score += max(0.0, 1.0 - min(1.0, node.latency_ms / 500.0)) * 0.08

        if set(request.data_affinity) & set(node.data_locality):
            score += 0.10
            reasons.append("data affinity match")
        if node.id in request.prefer_nodes:
            score += 0.08
            reasons.append("preferred node")

        hint_penalty, hint_bonus, hint_reasons = _hint_adjustment(node.id, self._hints, request)
        score += hint_bonus
        score -= hint_penalty
        reasons.extend(hint_reasons)

        score = max(0.0, min(1.0, score))
        reasons.insert(0, f"score={score:.4f}")
        reasons.append(f"free_vram_after={free_vram_after:.2f}GB")
        return NodeScore(node.id, score, score > 0.0, tuple(reasons))


class PrewarmPlanner:
    """Turns hints and likely workloads into safe prewarm plans."""

    def build_plans(
        self,
        *,
        hints: Iterable[SchedulerHintImpact | Mapping[str, Any]],
        workloads: Iterable[WorkloadRequest],
        nodes: Iterable[NodeState],
    ) -> tuple[PrewarmPlan, ...]:
        hint_list = [_coerce_hint(hint) for hint in hints]
        node_map = {node.id: node for node in nodes}
        plans: list[PrewarmPlan] = []
        for hint in hint_list:
            if hint.action != HintAction.PREWARM:
                continue
            node = node_map.get(hint.target)
            if node is None or not node.enabled or not node.healthy:
                continue
            model_id = hint.metadata.get("model_id")
            if model_id is None:
                model_id = _select_model_for_node(hint.target, workloads)
            if not model_id:
                continue
            plans.append(
                PrewarmPlan(
                    id=f"pw_{uuid.uuid4().hex[:20]}",
                    target_node=hint.target,
                    model_id=str(model_id),
                    reason=hint.reason,
                    priority=max(0, min(100, int(hint.priority))),
                    actions=("reserve runtime slot", "load model weights", "verify model health"),
                )
            )
        return tuple(sorted(plans, key=lambda item: item.priority, reverse=True))


def _validate_node(node: NodeState) -> None:
    if not node.id:
        raise ValueError("node id is required")
    for field_name in ("cpu_cores", "free_cpu_cores", "memory_gb", "free_memory_gb", "gpu_vram_gb", "free_vram_gb", "latency_ms"):
        value = float(getattr(node, field_name))
        if value < 0 or not math.isfinite(value):
            raise ValueError(f"{field_name} must be a finite non-negative number")
    if node.queue_depth < 0:
        raise ValueError("queue_depth must be non-negative")
    if not 0.0 <= node.gpu_utilization <= 1.0:
        raise ValueError("gpu_utilization must be between 0 and 1")


def _validate_workload(request: WorkloadRequest) -> None:
    if not request.id:
        raise ValueError("request id is required")
    for field_name in ("estimated_cpu_cores", "estimated_memory_gb", "estimated_vram_gb"):
        value = float(getattr(request, field_name))
        if value < 0 or not math.isfinite(value):
            raise ValueError(f"{field_name} must be a finite non-negative number")


def _coerce_hint(hint: SchedulerHintImpact | Mapping[str, Any]) -> SchedulerHintImpact:
    if isinstance(hint, SchedulerHintImpact):
        return hint
    action = HintAction(str(hint.get("action")))
    return SchedulerHintImpact(
        action=action,
        target=str(hint.get("target")),
        priority=int(hint.get("priority", 0)),
        reason=str(hint.get("reason", "")),
        metadata=dict(hint.get("metadata", {}) or {}),
    )


def _hint_adjustment(node_id: str, hints: Sequence[SchedulerHintImpact], request: WorkloadRequest) -> tuple[float, float, list[str]]:
    penalty = 0.0
    bonus = 0.0
    reasons: list[str] = []
    for hint in hints:
        if hint.target != node_id:
            continue
        weight = max(0.0, min(1.0, hint.priority / 100.0))
        if hint.action == HintAction.HOLD_CAPACITY and request.priority != WorkloadPriority.CRITICAL:
            penalty += 0.20 * weight
            reasons.append("hint=hold_capacity")
        elif hint.action == HintAction.THROTTLE_BACKGROUND and request.kind in {WorkloadKind.BATCH_INFERENCE, WorkloadKind.INDEXING, WorkloadKind.MAINTENANCE}:
            penalty += 0.25 * weight
            reasons.append("hint=throttle_background")
        elif hint.action == HintAction.SHIFT_LOAD and not request.interactive:
            penalty += 0.18 * weight
            reasons.append("hint=shift_load")
        elif hint.action == HintAction.PREWARM:
            model_id = hint.metadata.get("model_id")
            if model_id is None or model_id == request.model_id:
                bonus += 0.12 * weight
                reasons.append("hint=prewarm")
        elif hint.action == HintAction.SCALE_DOWN:
            penalty += 0.10 * weight
            reasons.append("hint=scale_down")
        elif hint.action == HintAction.SCALE_UP:
            bonus += 0.06 * weight
            reasons.append("hint=scale_up")
    return penalty, bonus, reasons


def _ratio(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, value / total))


def _join_reasons(scores: Sequence[NodeScore]) -> str:
    if not scores:
        return "no nodes registered"
    parts = []
    for score in scores:
        parts.append(f"{score.node_id}: {', '.join(score.reasons)}")
    return " | ".join(parts)


def _select_model_for_node(node_id: str, workloads: Iterable[WorkloadRequest]) -> str | None:
    for workload in workloads:
        if workload.model_id and (not workload.prefer_nodes or node_id in workload.prefer_nodes):
            return workload.model_id
    return None
