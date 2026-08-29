"""CyberHIVE Node Worker Runtime Loop MVP.

Patch 020 reconciled controller-side delivery, ACK and action-result state. This
module adds the node-local runtime loop that receives one signed ACTION envelope,
acknowledges it, runs an explicit handler through a local resource guard, and
returns a signed ACTION_RESULT envelope.

This is still not arbitrary execution. The worker runtime does not open network
sockets, run shell commands, start Docker, move files, or escalate privileges. It
only models the node-side lifecycle that later transports and sandboxes can plug
into.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
import json
import uuid

from .action_handlers import ActionHandlerContext, ActionHandlerRegistry
from .node_agent import AgentActionRequest, AgentActionResult, AgentActionStatus, AgentActionType
from .resource_guard import LocalResourceGuard, ResourceReservation, resource_request_for_action_payload
from .secure_channel import (
    ChannelDecision,
    ChannelDirection,
    ChannelPurpose,
    ChannelVerification,
    SecureChannel,
    SignedChannelEnvelope,
)


class WorkerRuntimeError(RuntimeError):
    """Raised when a worker runtime operation is invalid."""


class WorkerEnvelopeStatus(str, Enum):
    ACKED = "acked"
    HANDLED = "handled"
    DENIED = "denied"
    FAILED = "failed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class WorkerRuntimePolicy:
    """Local worker runtime policy."""

    send_ack_before_handle: bool = True
    require_resource_guard: bool = True
    max_result_payload_bytes: int = 64 * 1024

    def __post_init__(self) -> None:
        if self.max_result_payload_bytes < 1024:
            raise WorkerRuntimeError("max_result_payload_bytes must be at least 1024")


@dataclass(frozen=True)
class WorkerProcessOutcome:
    """Outcome for processing one controller-to-node action envelope."""

    envelope_id: str
    node_id: str
    status: WorkerEnvelopeStatus
    reason: str
    verification: ChannelVerification
    ack_envelope: SignedChannelEnvelope | None = None
    result_envelope: SignedChannelEnvelope | None = None
    action_result: AgentActionResult | None = None
    resource_reservation: ResourceReservation | None = None
    created_at: datetime = field(default_factory=_now)
    id: str = field(default_factory=lambda: f"wout_{uuid.uuid4().hex[:20]}")

    @property
    def ok(self) -> bool:
        return self.status in {WorkerEnvelopeStatus.ACKED, WorkerEnvelopeStatus.HANDLED}

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "envelope_id": self.envelope_id,
            "node_id": self.node_id,
            "status": self.status.value,
            "reason": self.reason,
            "verification": self.verification.as_dict(),
            "ack_envelope": None if self.ack_envelope is None else self.ack_envelope.as_dict(include_signature=False),
            "result_envelope": None if self.result_envelope is None else self.result_envelope.as_dict(include_signature=False),
            "action_result": None if self.action_result is None else self.action_result.as_dict(),
            "resource_reservation": None if self.resource_reservation is None else self.resource_reservation.as_dict(),
            "created_at": self.created_at.isoformat(),
        }


class NodeWorkerRuntime:
    """Node-local runtime loop for signed controller ACTION envelopes."""

    def __init__(
        self,
        *,
        node_id: str,
        session_id: str,
        session_token: str,
        channel: SecureChannel,
        handlers: ActionHandlerRegistry,
        resource_guard: LocalResourceGuard | None = None,
        policy: WorkerRuntimePolicy | None = None,
    ) -> None:
        if not node_id:
            raise WorkerRuntimeError("node_id is required")
        if not session_id:
            raise WorkerRuntimeError("session_id is required")
        if not session_token:
            raise WorkerRuntimeError("session_token is required")
        self.node_id = node_id
        self.session_id = session_id
        self.session_token = session_token
        self.channel = channel
        self.handlers = handlers
        self.resource_guard = resource_guard
        self.policy = policy or WorkerRuntimePolicy()
        self.outcomes: list[WorkerProcessOutcome] = []
        self.outbox: list[SignedChannelEnvelope] = []
        self._next_sequence: dict[ChannelPurpose, int] = {}

    def process_action_envelope(self, envelope: SignedChannelEnvelope, *, now: datetime | None = None) -> WorkerProcessOutcome:
        current = now or _now()
        verification = self.channel.verify(
            envelope,
            session_token=self.session_token,
            expected_direction=ChannelDirection.CONTROLLER_TO_NODE,
            expected_purpose=ChannelPurpose.ACTION,
            now=current,
        )
        if not verification.accepted:
            outcome = self._denied_outcome(envelope, verification, "action envelope denied by secure channel")
            self._record(outcome)
            return outcome

        payload = dict(envelope.payload)
        action_payload = _mapping(payload.get("payload"))
        try:
            action = _action_from_payload(payload)
        except WorkerRuntimeError as exc:
            result = self._synthetic_parse_failure_result(envelope, str(exc), current)
            result_envelope = self._build_result(envelope, result, current, delivery_id=envelope.correlation_id)
            outcome = WorkerProcessOutcome(
                envelope_id=envelope.id,
                node_id=envelope.node_id,
                status=WorkerEnvelopeStatus.DENIED,
                reason=result.reason,
                verification=verification,
                ack_envelope=None,
                result_envelope=result_envelope,
                action_result=result,
                created_at=current,
            )
            self._record(outcome)
            return outcome

        ack = self._build_ack(envelope, current)
        dry_run = bool(payload.get("dry_run", True))
        approval_tokens = tuple(str(value) for value in payload.get("approval_tokens", ()))
        requested_by = str(payload.get("requested_by", "node-worker-runtime"))
        delivery_id = envelope.correlation_id

        reservation = None
        if self.resource_guard is not None:
            try:
                reservation = self.resource_guard.reserve(
                    action=action.value,
                    request=resource_request_for_action_payload(action.value, action_payload),
                    dry_run=dry_run,
                    now=current,
                )
            except Exception as exc:
                result = self._synthetic_result(envelope, action, AgentActionStatus.DENIED, f"resource guard error: {exc}", current)
                result_envelope = self._build_result(envelope, result, current, delivery_id=delivery_id)
                outcome = WorkerProcessOutcome(
                    envelope_id=envelope.id,
                    node_id=envelope.node_id,
                    status=WorkerEnvelopeStatus.DENIED,
                    reason=result.reason,
                    verification=verification,
                    ack_envelope=ack,
                    result_envelope=result_envelope,
                    action_result=result,
                    resource_reservation=None,
                    created_at=current,
                )
                self._record(outcome)
                return outcome
            if not reservation.granted:
                result = self._synthetic_result(envelope, action, AgentActionStatus.DENIED, reservation.reason, current)
                result_envelope = self._build_result(envelope, result, current, delivery_id=delivery_id, reservation=reservation)
                outcome = WorkerProcessOutcome(
                    envelope_id=envelope.id,
                    node_id=envelope.node_id,
                    status=WorkerEnvelopeStatus.DENIED,
                    reason=reservation.reason,
                    verification=verification,
                    ack_envelope=ack,
                    result_envelope=result_envelope,
                    action_result=result,
                    resource_reservation=reservation,
                    created_at=current,
                )
                self._record(outcome)
                return outcome
        elif self.policy.require_resource_guard:
            result = self._synthetic_result(envelope, action, AgentActionStatus.DENIED, "resource guard required by worker policy", current)
            result_envelope = self._build_result(envelope, result, current, delivery_id=delivery_id)
            outcome = WorkerProcessOutcome(
                envelope_id=envelope.id,
                node_id=envelope.node_id,
                status=WorkerEnvelopeStatus.DENIED,
                reason=result.reason,
                verification=verification,
                ack_envelope=ack,
                result_envelope=result_envelope,
                action_result=result,
                created_at=current,
            )
            self._record(outcome)
            return outcome

        context = ActionHandlerContext(
            node_id=self.node_id,
            session_id=self.session_id,
            delivery_id=delivery_id,
            correlation_id=envelope.correlation_id,
            requested_by=requested_by,
            dry_run=dry_run,
            approval_tokens=approval_tokens,
            resource_reservation_id=None if reservation is None else reservation.id,
            metadata={"envelope_id": envelope.id},
        )
        request = AgentActionRequest(
            target_node=self.node_id,
            action=action,
            payload=action_payload,
            dry_run=dry_run,
            approval_tokens=approval_tokens,
            requested_by=requested_by,
            correlation_id=envelope.correlation_id,
        )
        result = self.handlers.dispatch(request, context)
        if reservation is not None and reservation.active:
            self.resource_guard.release(reservation.id, reason=f"action finished: {result.status.value}", now=current)
        result_envelope = self._build_result(envelope, result, current, delivery_id=delivery_id, reservation=reservation)
        status = WorkerEnvelopeStatus.HANDLED if result.ok else WorkerEnvelopeStatus.FAILED
        outcome = WorkerProcessOutcome(
            envelope_id=envelope.id,
            node_id=envelope.node_id,
            status=status,
            reason=result.reason,
            verification=verification,
            ack_envelope=ack,
            result_envelope=result_envelope,
            action_result=result,
            resource_reservation=reservation,
            created_at=current,
        )
        self._record(outcome)
        return outcome

    def _build_ack(self, envelope: SignedChannelEnvelope, now: datetime) -> SignedChannelEnvelope:
        ack = self.channel.build_envelope(
            node_id=self.node_id,
            session_id=self.session_id,
            direction=ChannelDirection.NODE_TO_CONTROLLER,
            purpose=ChannelPurpose.ACK,
            sequence=self._next(ChannelPurpose.ACK),
            payload={
                "ack_for": envelope.id,
                "envelope_id": envelope.id,
                "delivery_id": envelope.correlation_id,
                "correlation_id": envelope.correlation_id,
                "status": "accepted",
            },
            session_token=self.session_token,
            issued_at=now,
            correlation_id=envelope.correlation_id,
        )
        self.outbox.append(ack)
        return ack

    def _build_result(
        self,
        envelope: SignedChannelEnvelope,
        result: AgentActionResult,
        now: datetime,
        *,
        delivery_id: str | None,
        reservation: ResourceReservation | None = None,
    ) -> SignedChannelEnvelope:
        payload = {
            "delivery_id": delivery_id,
            "correlation_id": envelope.correlation_id,
            "ack_for": envelope.id,
            "envelope_id": envelope.id,
            "request_id": result.request_id,
            "action_request_id": result.request_id,
            "action": result.action.value,
            "status": result.status.value,
            "reason": result.reason,
            "metadata": dict(result.metadata),
            "events": list(result.events),
            "resource_reservation_id": None if reservation is None else reservation.id,
        }
        payload = self._bounded_result_payload(payload)
        result_envelope = self.channel.build_envelope(
            node_id=self.node_id,
            session_id=self.session_id,
            direction=ChannelDirection.NODE_TO_CONTROLLER,
            purpose=ChannelPurpose.ACTION_RESULT,
            sequence=self._next(ChannelPurpose.ACTION_RESULT),
            payload=payload,
            session_token=self.session_token,
            issued_at=now,
            correlation_id=envelope.correlation_id,
        )
        self.outbox.append(result_envelope)
        return result_envelope

    def _synthetic_result(
        self,
        envelope: SignedChannelEnvelope,
        action: AgentActionType,
        status: AgentActionStatus,
        reason: str,
        now: datetime,
    ) -> AgentActionResult:
        return AgentActionResult(
            request_id=f"synthetic_{envelope.id}",
            target_node=self.node_id,
            action=action,
            status=status,
            reason=reason,
            created_at=now,
            completed_at=now,
            metadata={"envelope_id": envelope.id},
        )

    def _synthetic_parse_failure_result(self, envelope: SignedChannelEnvelope, reason: str, now: datetime) -> AgentActionResult:
        return AgentActionResult(
            request_id=f"synthetic_{envelope.id}",
            target_node=self.node_id,
            action=AgentActionType.NOOP,
            status=AgentActionStatus.DENIED,
            reason=reason,
            created_at=now,
            completed_at=now,
            metadata={
                "envelope_id": envelope.id,
                "requested_action": envelope.payload.get("action"),
                "parse_failure": True,
            },
        )

    def _result_payload_bytes(self, payload: Mapping[str, Any]) -> int:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return len(encoded)

    def _bounded_result_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload_bytes = self._result_payload_bytes(payload)
        if payload_bytes <= self.policy.max_result_payload_bytes:
            return payload

        bounded = dict(payload)
        bounded["status"] = AgentActionStatus.FAILED.value
        bounded["reason"] = "result payload exceeded max_result_payload_bytes"
        bounded["metadata"] = {
            "result_payload_truncated": True,
            "original_payload_bytes": payload_bytes,
            "max_result_payload_bytes": self.policy.max_result_payload_bytes,
            "original_status": payload.get("status"),
        }
        bounded["events"] = []
        if self._result_payload_bytes(bounded) <= self.policy.max_result_payload_bytes:
            return bounded

        bounded["metadata"] = {"result_payload_truncated": True}
        return bounded

    def _denied_outcome(self, envelope: SignedChannelEnvelope, verification: ChannelVerification, reason: str) -> WorkerProcessOutcome:
        status = WorkerEnvelopeStatus.DENIED if verification.status != ChannelDecision.STALE else WorkerEnvelopeStatus.FAILED
        return WorkerProcessOutcome(
            envelope_id=envelope.id,
            node_id=envelope.node_id,
            status=status,
            reason=reason,
            verification=verification,
        )

    def _next(self, purpose: ChannelPurpose) -> int:
        value = self._next_sequence.get(purpose, 0) + 1
        self._next_sequence[purpose] = value
        return value

    def _record(self, outcome: WorkerProcessOutcome) -> None:
        self.outcomes.append(outcome)

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "session_id": self.session_id,
            "outcomes": [outcome.as_dict() for outcome in self.outcomes],
            "outbox": [envelope.as_dict(include_signature=False) for envelope in self.outbox],
        }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _action_from_payload(payload: Mapping[str, Any]) -> AgentActionType:
    action_value = payload.get("action")
    try:
        return AgentActionType(str(action_value))
    except ValueError as exc:
        raise WorkerRuntimeError(f"unsupported action: {action_value}") from exc
