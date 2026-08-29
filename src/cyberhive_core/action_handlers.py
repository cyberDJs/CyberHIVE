"""CyberHIVE Action Handler Registry MVP.

Node Agent MVP gave CyberHIVE a typed action boundary. This module adds a
handler registry so a node runtime can resolve actions by type without hard
wiring every future action into a single dispatcher class.

The MVP is intentionally boring:

* handlers are explicit Python callables,
* unknown actions fail closed,
* dry-run is preserved end-to-end,
* payload size/action validation still lives in the node agent boundary,
* no shell, Docker, SSH or host mutation is introduced here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

from .node_agent import (
    AgentActionRequest,
    AgentActionResult,
    AgentActionStatus,
    AgentActionType,
    LocalNodeAgent,
)


class ActionHandlerError(RuntimeError):
    """Raised when action handler registration or dispatch is invalid."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ActionHandlerContext:
    """Execution context passed to a node-local action handler."""

    node_id: str
    session_id: str | None = None
    delivery_id: str | None = None
    correlation_id: str | None = None
    requested_by: str = "node-worker-runtime"
    dry_run: bool = True
    approval_tokens: tuple[str, ...] = ()
    resource_reservation_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "session_id": self.session_id,
            "delivery_id": self.delivery_id,
            "correlation_id": self.correlation_id,
            "requested_by": self.requested_by,
            "dry_run": self.dry_run,
            "approval_tokens": list(self.approval_tokens),
            "resource_reservation_id": self.resource_reservation_id,
            "metadata": dict(self.metadata),
        }


ActionHandler = Callable[[AgentActionRequest, ActionHandlerContext], AgentActionResult]


@dataclass(frozen=True)
class RegisteredActionHandler:
    """Metadata and callable for one action handler."""

    action: AgentActionType
    handler: ActionHandler
    description: str = ""
    dry_run_safe: bool = True
    live_safe: bool = False
    required_capabilities: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "description": self.description,
            "dry_run_safe": self.dry_run_safe,
            "live_safe": self.live_safe,
            "required_capabilities": list(self.required_capabilities),
            "metadata": dict(self.metadata),
        }


class ActionHandlerRegistry:
    """Fail-closed registry for node-local action handlers."""

    def __init__(self) -> None:
        self._handlers: dict[AgentActionType, RegisteredActionHandler] = {}
        self.dispatch_log: list[dict[str, Any]] = []

    def register(
        self,
        action: AgentActionType | str,
        handler: ActionHandler,
        *,
        description: str = "",
        dry_run_safe: bool = True,
        live_safe: bool = False,
        required_capabilities: Iterable[str] = (),
        metadata: Mapping[str, Any] | None = None,
        replace: bool = False,
    ) -> RegisteredActionHandler:
        action_type = _coerce_action(action)
        if action_type in self._handlers and not replace:
            raise ActionHandlerError(f"handler already registered for action: {action_type.value}")
        registered = RegisteredActionHandler(
            action=action_type,
            handler=handler,
            description=description,
            dry_run_safe=dry_run_safe,
            live_safe=live_safe,
            required_capabilities=tuple(str(value) for value in required_capabilities),
            metadata=metadata or {},
        )
        self._handlers[action_type] = registered
        return registered

    def unregister(self, action: AgentActionType | str) -> bool:
        return self._handlers.pop(_coerce_action(action), None) is not None

    def has(self, action: AgentActionType | str) -> bool:
        return _coerce_action(action) in self._handlers

    def require(self, action: AgentActionType | str) -> RegisteredActionHandler:
        action_type = _coerce_action(action)
        handler = self._handlers.get(action_type)
        if handler is None:
            raise ActionHandlerError(f"no handler registered for action: {action_type.value}")
        return handler

    def registered_actions(self) -> tuple[str, ...]:
        return tuple(sorted(action.value for action in self._handlers))

    def dispatch(self, request: AgentActionRequest, context: ActionHandlerContext | None = None) -> AgentActionResult:
        if not isinstance(request.action, AgentActionType):
            raise ActionHandlerError("request.action must be AgentActionType")
        context = context or ActionHandlerContext(node_id=request.target_node, dry_run=request.dry_run)
        try:
            registered = self.require(request.action)
        except ActionHandlerError as exc:
            result = _synthetic_result(request, AgentActionStatus.DENIED, str(exc), context=context)
            self._record(request, context, result, registered=False)
            return result
        if request.dry_run and not registered.dry_run_safe:
            result = _synthetic_result(request, AgentActionStatus.DENIED, "handler is not dry-run safe", context=context)
            self._record(request, context, result, registered=True)
            return result
        if not request.dry_run and not registered.live_safe:
            result = _synthetic_result(request, AgentActionStatus.DENIED, "handler is not live-safe", context=context)
            self._record(request, context, result, registered=True)
            return result
        try:
            result = registered.handler(request, context)
        except Exception as exc:  # pragma: no cover - defensive boundary.
            result = _synthetic_result(request, AgentActionStatus.FAILED, f"handler raised {type(exc).__name__}: {exc}", context=context)
        self._record(request, context, result, registered=True)
        return result

    def describe(self) -> dict[str, Any]:
        return {
            "handlers": [handler.as_dict() for handler in self._handlers.values()],
            "dispatch_log": list(self.dispatch_log),
        }

    def _record(self, request: AgentActionRequest, context: ActionHandlerContext, result: AgentActionResult, *, registered: bool) -> None:
        self.dispatch_log.append(
            {
                "request_id": request.id,
                "action": request.action.value,
                "target_node": request.target_node,
                "registered": registered,
                "status": result.status.value,
                "context": context.as_dict(),
            }
        )


def build_agent_handler_registry(agent: LocalNodeAgent, *, live_safe: bool = False) -> ActionHandlerRegistry:
    """Expose an existing LocalNodeAgent through ActionHandlerRegistry."""

    registry = ActionHandlerRegistry()
    for action_name in agent.descriptor.normalized_actions():
        action = _coerce_action(action_name)
        registry.register(
            action,
            _agent_handler(agent),
            description=f"LocalNodeAgent handler for {action.value}",
            dry_run_safe=True,
            live_safe=live_safe,
            metadata={"node_id": agent.descriptor.id},
            replace=True,
        )
    return registry


def _agent_handler(agent: LocalNodeAgent) -> ActionHandler:
    def handle(request: AgentActionRequest, context: ActionHandlerContext) -> AgentActionResult:
        return agent.handle(request)

    return handle


def _coerce_action(action: AgentActionType | str) -> AgentActionType:
    if isinstance(action, AgentActionType):
        return action
    try:
        return AgentActionType(str(action))
    except ValueError as exc:
        raise ActionHandlerError(f"unsupported action: {action}") from exc


def _synthetic_result(
    request: AgentActionRequest,
    status: AgentActionStatus,
    reason: str,
    *,
    context: ActionHandlerContext,
) -> AgentActionResult:
    current = _now()
    return AgentActionResult(
        request_id=request.id,
        target_node=request.target_node,
        action=request.action,
        status=status,
        reason=reason,
        created_at=current,
        completed_at=current,
        metadata={"context": context.as_dict()},
    )
