"""CyberHIVE Node Agent & Action Dispatch MVP.

Structured node-side action dispatch for approved orchestration plans.

The MVP intentionally does not run shell commands, open SSH sessions or perform
remote execution. It gives CyberHIVE a typed, auditable boundary between the
central execution/governance layers and node-local side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Iterable, Mapping
import uuid

try:  # Optional integration with the runtime bus from Patch 002.
    from .hiveframe import Operation, OperationType
    from .runtime_bus import RuntimeBus
except Exception:  # pragma: no cover - keeps module importable in isolation.
    Operation = None  # type: ignore[assignment]
    OperationType = None  # type: ignore[assignment]
    RuntimeBus = None  # type: ignore[assignment]

from .integration_orchestrator import OrchestrationPlan
from .scheduler_router import PrewarmPlan


class AgentActionType(str, Enum):
    HEALTH_CHECK = "health_check"
    PREWARM_MODEL = "prewarm_model"
    DATA_MOVE = "data_move"
    CACHE_PRIME = "cache_prime"
    NOOP = "noop"


class AgentActionStatus(str, Enum):
    ACCEPTED = "accepted"
    DRY_RUN = "dry_run"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    DENIED = "denied"
    FAILED = "failed"


class NodeAgentError(RuntimeError):
    """Raised when an agent action cannot be dispatched or handled."""


@dataclass(frozen=True)
class NodeDescriptor:
    """Safe public descriptor of a CyberHIVE node agent."""

    id: str
    enabled: bool = True
    healthy: bool = True
    capabilities: tuple[str, ...] = ()
    allowed_actions: tuple[AgentActionType | str, ...] = (
        AgentActionType.HEALTH_CHECK,
        AgentActionType.NOOP,
    )
    labels: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def normalized_actions(self) -> tuple[str, ...]:
        return tuple(action.value if isinstance(action, AgentActionType) else str(action) for action in self.allowed_actions)

    def supports_action(self, action: AgentActionType | str) -> bool:
        value = action.value if isinstance(action, AgentActionType) else str(action)
        return value in self.normalized_actions()

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "enabled": self.enabled,
            "healthy": self.healthy,
            "capabilities": list(self.capabilities),
            "allowed_actions": list(self.normalized_actions()),
            "labels": dict(self.labels),
            "metadata": dict(self.metadata),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class AgentActionRequest:
    """Typed action request sent to a node agent."""

    target_node: str
    action: AgentActionType
    payload: Mapping[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    approval_tokens: tuple[str, ...] = ()
    requested_by: str = "system"
    correlation_id: str | None = None
    id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:20]}")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_node": self.target_node,
            "action": self.action.value,
            "payload": dict(self.payload),
            "dry_run": self.dry_run,
            "approval_tokens": list(self.approval_tokens),
            "requested_by": self.requested_by,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class AgentActionResult:
    """Result returned by a node agent."""

    request_id: str
    target_node: str
    action: AgentActionType
    status: AgentActionStatus
    reason: str
    created_at: datetime
    completed_at: datetime
    id: str = field(default_factory=lambda: f"ares_{uuid.uuid4().hex[:20]}")
    metadata: Mapping[str, Any] = field(default_factory=dict)
    events: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in {AgentActionStatus.DRY_RUN, AgentActionStatus.SUCCEEDED, AgentActionStatus.SKIPPED}

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "target_node": self.target_node,
            "action": self.action.value,
            "status": self.status.value,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "metadata": dict(self.metadata),
            "events": list(self.events),
        }


@dataclass(frozen=True)
class NodeAgentPolicy:
    """Local node-side safety gates.

    Approval workflow is still authoritative above this layer. The node agent
    repeats the critical checks because side-effect boundaries should be boring
    and redundant, not clever and fragile.
    """

    allow_live_actions: bool = False
    allow_prewarm: bool = False
    allow_data_moves: bool = False
    allow_cache_prime: bool = False
    max_payload_bytes: int = 64 * 1024
    required_prewarm_token: str = "runtime.prewarm.execute"
    required_data_move_token: str = "data.move.execute"
    required_cache_prime_token: str = "cache.prime.execute"


class LocalNodeAgent:
    """Deterministic in-memory node agent.

    The MVP simulates side effects by recording node-local state. It never calls
    a shell, never performs SSH and never moves files directly.
    """

    def __init__(self, descriptor: NodeDescriptor, *, policy: NodeAgentPolicy | None = None) -> None:
        _validate_descriptor(descriptor)
        self.descriptor = descriptor
        self.policy = policy or NodeAgentPolicy()
        self.warmed_models: set[str] = set()
        self.handled_requests: list[str] = []

    def handle(self, request: AgentActionRequest) -> AgentActionResult:
        _validate_request(request)
        started = datetime.now(timezone.utc)

        denial = self._preflight(request)
        if denial is not None:
            return self._result(request, AgentActionStatus.DENIED, denial, started)

        if request.dry_run:
            return self._result(
                request,
                AgentActionStatus.DRY_RUN,
                "dry-run accepted; no node-local side effects executed",
                started,
                metadata={"would_execute": request.action.value},
            )

        if request.action == AgentActionType.HEALTH_CHECK:
            return self._result(request, AgentActionStatus.SUCCEEDED, "node health check succeeded", started, metadata=self.descriptor.as_dict())

        if request.action == AgentActionType.NOOP:
            return self._result(request, AgentActionStatus.SKIPPED, "noop action skipped", started)

        if request.action == AgentActionType.PREWARM_MODEL:
            model_id = str(request.payload.get("model_id") or "")
            if not model_id:
                return self._result(request, AgentActionStatus.FAILED, "prewarm_model requires payload.model_id", started)
            self.warmed_models.add(model_id)
            return self._result(
                request,
                AgentActionStatus.SUCCEEDED,
                f"model prewarm recorded for {model_id}",
                started,
                metadata={"model_id": model_id, "warmed_models": sorted(self.warmed_models)},
                events=(f"prewarm:{model_id}",),
            )

        if request.action == AgentActionType.DATA_MOVE:
            return self._result(
                request,
                AgentActionStatus.SKIPPED,
                "data move accepted but physical mover is not invoked by Node Agent MVP",
                started,
                metadata=dict(request.payload),
            )

        if request.action == AgentActionType.CACHE_PRIME:
            return self._result(
                request,
                AgentActionStatus.SKIPPED,
                "cache prime accepted but cache backend is not mutated by Node Agent MVP",
                started,
                metadata=dict(request.payload),
            )

        return self._result(request, AgentActionStatus.FAILED, f"unsupported action: {request.action.value}", started)

    def _preflight(self, request: AgentActionRequest) -> str | None:
        if request.target_node != self.descriptor.id:
            return f"request targets {request.target_node}, agent is {self.descriptor.id}"
        if not self.descriptor.enabled:
            return "node agent is disabled"
        if not self.descriptor.healthy:
            return "node agent is unhealthy"
        if not self.descriptor.supports_action(request.action):
            return f"action {request.action.value} is not allowed on node {self.descriptor.id}"
        payload_size = len(json.dumps(dict(request.payload), ensure_ascii=False, sort_keys=True).encode("utf-8"))
        if payload_size > self.policy.max_payload_bytes:
            return f"payload exceeds max_payload_bytes ({payload_size}>{self.policy.max_payload_bytes})"
        if request.dry_run:
            return None
        if not self.policy.allow_live_actions:
            return "live node actions disabled by node agent policy"
        approvals = set(request.approval_tokens)
        if request.action == AgentActionType.PREWARM_MODEL:
            if not self.policy.allow_prewarm:
                return "prewarm disabled by node agent policy"
            if self.policy.required_prewarm_token not in approvals:
                return f"missing approval token: {self.policy.required_prewarm_token}"
        if request.action == AgentActionType.DATA_MOVE:
            if not self.policy.allow_data_moves:
                return "data moves disabled by node agent policy"
            if self.policy.required_data_move_token not in approvals:
                return f"missing approval token: {self.policy.required_data_move_token}"
        if request.action == AgentActionType.CACHE_PRIME:
            if not self.policy.allow_cache_prime:
                return "cache prime disabled by node agent policy"
            if self.policy.required_cache_prime_token not in approvals:
                return f"missing approval token: {self.policy.required_cache_prime_token}"
        return None

    def _result(
        self,
        request: AgentActionRequest,
        status: AgentActionStatus,
        reason: str,
        started: datetime,
        *,
        metadata: Mapping[str, Any] | None = None,
        events: Iterable[str] = (),
    ) -> AgentActionResult:
        self.handled_requests.append(request.id)
        return AgentActionResult(
            request_id=request.id,
            target_node=self.descriptor.id,
            action=request.action,
            status=status,
            reason=reason,
            created_at=started,
            completed_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            events=tuple(events),
        )


class NodeAgentRegistry:
    """Registry and dispatcher for local node agents."""

    def __init__(self, *, runtime_bus: Any | None = None) -> None:
        self.runtime_bus = runtime_bus
        self._agents: dict[str, LocalNodeAgent] = {}

    def register(self, agent: LocalNodeAgent) -> None:
        if agent.descriptor.id in self._agents:
            raise NodeAgentError(f"node agent already registered: {agent.descriptor.id}")
        self._agents[agent.descriptor.id] = agent

    def upsert(self, agent: LocalNodeAgent) -> None:
        self._agents[agent.descriptor.id] = agent

    def get(self, node_id: str) -> LocalNodeAgent:
        try:
            return self._agents[node_id]
        except KeyError as exc:
            raise NodeAgentError(f"no node agent registered for {node_id}") from exc

    def descriptors(self) -> tuple[NodeDescriptor, ...]:
        return tuple(agent.descriptor for agent in self._agents.values())

    def dispatch(self, request: AgentActionRequest) -> AgentActionResult:
        result = self.get(request.target_node).handle(request)
        self._publish(result)
        return result

    def dispatch_many(self, requests: Iterable[AgentActionRequest]) -> tuple[AgentActionResult, ...]:
        return tuple(self.dispatch(request) for request in requests)

    def _publish(self, result: AgentActionResult) -> None:
        if self.runtime_bus is None or Operation is None or OperationType is None:
            return
        self.runtime_bus.publish(
            Operation.from_json_payload(
                OperationType.RESULT,
                f"node_agent.{result.target_node}.{result.action.value}.{result.request_id}",
                result.as_dict(),
            )
        )


class NodeActionDispatcher:
    """Builds and dispatches node-agent actions from orchestration plans."""

    def __init__(self, registry: NodeAgentRegistry) -> None:
        self.registry = registry

    def build_requests(
        self,
        plan: OrchestrationPlan,
        *,
        dry_run: bool = True,
        approval_tokens: Iterable[str] = (),
        requested_by: str = "system",
    ) -> tuple[AgentActionRequest, ...]:
        target_node = None if plan.route_decision is None else plan.route_decision.target_node
        requests: list[AgentActionRequest] = []

        for prewarm in plan.prewarm:
            requests.append(_prewarm_request(prewarm, dry_run=dry_run, approval_tokens=approval_tokens, requested_by=requested_by, correlation_id=plan.id))

        if plan.data_moves and target_node:
            for move in plan.data_moves:
                requests.append(
                    AgentActionRequest(
                        target_node=target_node,
                        action=AgentActionType.DATA_MOVE,
                        payload={
                            "object_id": move.object_id,
                            "action": move.action.value,
                            "from_tier": None if move.from_tier is None else move.from_tier.value,
                            "to_tier": move.to_tier.value,
                            "replicas": move.replicas,
                            "target_devices": list(move.target_devices),
                            "reason": move.reason,
                        },
                        dry_run=dry_run,
                        approval_tokens=tuple(approval_tokens),
                        requested_by=requested_by,
                        correlation_id=plan.id,
                    )
                )

        return tuple(requests)

    def dispatch_plan(
        self,
        plan: OrchestrationPlan,
        *,
        dry_run: bool = True,
        approval_tokens: Iterable[str] = (),
        requested_by: str = "system",
    ) -> tuple[AgentActionResult, ...]:
        return self.registry.dispatch_many(
            self.build_requests(plan, dry_run=dry_run, approval_tokens=approval_tokens, requested_by=requested_by)
        )


def _prewarm_request(
    prewarm: PrewarmPlan,
    *,
    dry_run: bool,
    approval_tokens: Iterable[str],
    requested_by: str,
    correlation_id: str,
) -> AgentActionRequest:
    return AgentActionRequest(
        target_node=prewarm.target_node,
        action=AgentActionType.PREWARM_MODEL,
        payload={
            "model_id": prewarm.model_id,
            "reason": prewarm.reason,
            "priority": prewarm.priority,
            "actions": list(prewarm.actions),
        },
        dry_run=dry_run,
        approval_tokens=tuple(approval_tokens),
        requested_by=requested_by,
        correlation_id=correlation_id,
    )


def _validate_descriptor(descriptor: NodeDescriptor) -> None:
    if not descriptor.id:
        raise NodeAgentError("node descriptor id is required")
    for action in descriptor.allowed_actions:
        value = action.value if isinstance(action, AgentActionType) else str(action)
        try:
            AgentActionType(value)
        except ValueError as exc:
            raise NodeAgentError(f"unsupported allowed action: {value}") from exc


def _validate_request(request: AgentActionRequest) -> None:
    if not request.id:
        raise NodeAgentError("action request id is required")
    if not request.target_node:
        raise NodeAgentError("target_node is required")
    if not isinstance(request.action, AgentActionType):
        raise NodeAgentError("action must be AgentActionType")
