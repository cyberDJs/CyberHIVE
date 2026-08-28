"""CyberHIVE Secure Channel & Signed Message MVP.

This module provides dependency-free controller-side contracts for authenticated
node/controller messages. It deliberately does not open sockets, implement TLS,
perform remote execution, or encrypt payloads. Those belong to later transport
patches.

The MVP focuses on the boring but critical part:

* canonical message envelopes,
* HMAC signatures over enrolled node session tokens,
* strict message direction and purpose validation,
* timestamp freshness checks,
* monotonic sequence/replay protection,
* safe dispatch hooks for heartbeats and node-agent actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import hmac
import json
import math
from typing import Any, Mapping
import uuid

try:  # Optional Patch 014 integration.
    from .node_identity import NodeIdentityRegistry
except Exception:  # pragma: no cover
    NodeIdentityRegistry = None  # type: ignore[assignment]

try:  # Optional Patch 015 integration.
    from .node_heartbeat import NodeHeartbeat, NodeHeartbeatStore
except Exception:  # pragma: no cover
    NodeHeartbeat = None  # type: ignore[assignment]
    NodeHeartbeatStore = None  # type: ignore[assignment]

try:  # Optional Patch 013 integration.
    from .node_agent import AgentActionRequest, AgentActionType, NodeActionDispatcher
except Exception:  # pragma: no cover
    AgentActionRequest = None  # type: ignore[assignment]
    AgentActionType = None  # type: ignore[assignment]
    NodeActionDispatcher = None  # type: ignore[assignment]


class ChannelDirection(str, Enum):
    NODE_TO_CONTROLLER = "node_to_controller"
    CONTROLLER_TO_NODE = "controller_to_node"


class ChannelPurpose(str, Enum):
    HEARTBEAT = "heartbeat"
    ACTION = "action"
    ACTION_RESULT = "action_result"
    ACK = "ack"
    ERROR = "error"


class ChannelDecision(str, Enum):
    ACCEPT = "accept"
    DENY = "deny"
    DUPLICATE = "duplicate"
    STALE = "stale"


class SecureChannelError(RuntimeError):
    """Raised when secure channel inputs are invalid."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "as_dict"):
        return value.as_dict()
    if hasattr(value, "value"):
        return value.value
    return str(value)


def canonical_json(value: Mapping[str, Any]) -> str:
    """Return deterministic JSON used for message signatures."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def _sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _token_key(session_token: str) -> bytes:
    if not session_token:
        raise SecureChannelError("session_token is required")
    return hashlib.sha256(session_token.encode("utf-8")).digest()


def _validate_timestamp(value: datetime) -> None:
    if value.tzinfo is None:
        raise SecureChannelError("message timestamp must be timezone-aware")


def _finite_float(value: Any, *, field_name: str, minimum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SecureChannelError(f"{field_name} must be numeric") from exc
    if not math.isfinite(number):
        raise SecureChannelError(f"{field_name} must be finite")
    if minimum is not None and number < minimum:
        raise SecureChannelError(f"{field_name} must be >= {minimum}")
    return number


@dataclass(frozen=True)
class SignedChannelEnvelope:
    """Canonical signed message envelope between node and controller."""

    node_id: str
    session_id: str
    direction: ChannelDirection
    purpose: ChannelPurpose
    sequence: int
    payload: Mapping[str, Any]
    issued_at: datetime = field(default_factory=_now)
    expires_at: datetime | None = None
    correlation_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str | None = None
    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:20]}")

    def __post_init__(self) -> None:
        if not self.node_id or not self.node_id.strip():
            raise SecureChannelError("node_id is required")
        if not self.session_id or not self.session_id.strip():
            raise SecureChannelError("session_id is required")
        if int(self.sequence) <= 0:
            raise SecureChannelError("sequence must be positive")
        _validate_timestamp(self.issued_at)
        if self.expires_at is not None:
            _validate_timestamp(self.expires_at)
            if self.expires_at <= self.issued_at:
                raise SecureChannelError("expires_at must be after issued_at")

    def signing_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "session_id": self.session_id,
            "direction": self.direction.value,
            "purpose": self.purpose.value,
            "sequence": self.sequence,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
            "metadata": self.metadata,
        }

    def canonical_payload(self) -> bytes:
        return canonical_json(self.signing_payload()).encode("utf-8")

    def digest(self) -> str:
        return "sha256:" + _sha256_hex(self.canonical_payload())

    def with_signature(self, signature: str) -> "SignedChannelEnvelope":
        return replace(self, signature=signature)

    def sign(self, session_token: str) -> "SignedChannelEnvelope":
        signature = hmac.new(_token_key(session_token), self.canonical_payload(), hashlib.sha256).hexdigest()
        return self.with_signature(signature)

    def verify_signature(self, session_token: str) -> bool:
        if not self.signature:
            return False
        expected = hmac.new(_token_key(session_token), self.canonical_payload(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)

    def as_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        data = self.signing_payload()
        data.update({"digest": self.digest()})
        if include_signature:
            data["signature"] = self.signature
        return data


@dataclass(frozen=True)
class ChannelVerification:
    status: ChannelDecision
    envelope_id: str
    node_id: str
    reason: str
    findings: tuple[str, ...] = ()
    accepted_at: datetime = field(default_factory=_now)

    @property
    def accepted(self) -> bool:
        return self.status == ChannelDecision.ACCEPT

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "envelope_id": self.envelope_id,
            "node_id": self.node_id,
            "reason": self.reason,
            "findings": list(self.findings),
            "accepted_at": self.accepted_at.isoformat(),
        }


class ReplayGuard:
    """Tracks monotonic sequence numbers per session and direction."""

    def __init__(self) -> None:
        self._last_sequence: dict[tuple[str, ChannelDirection, ChannelPurpose], int] = {}
        self._accepted_digests: set[str] = set()

    def check(self, envelope: SignedChannelEnvelope) -> ChannelVerification | None:
        key = (envelope.session_id, envelope.direction, envelope.purpose)
        last = self._last_sequence.get(key, 0)
        if envelope.sequence <= last:
            return ChannelVerification(
                status=ChannelDecision.DUPLICATE,
                envelope_id=envelope.id,
                node_id=envelope.node_id,
                reason="sequence is not newer than last accepted message",
                findings=("replay-sequence",),
            )
        digest = envelope.digest()
        if digest in self._accepted_digests:
            return ChannelVerification(
                status=ChannelDecision.DUPLICATE,
                envelope_id=envelope.id,
                node_id=envelope.node_id,
                reason="message digest was already accepted",
                findings=("replay-digest",),
            )
        return None

    def accept(self, envelope: SignedChannelEnvelope) -> None:
        key = (envelope.session_id, envelope.direction, envelope.purpose)
        self._last_sequence[key] = max(self._last_sequence.get(key, 0), envelope.sequence)
        self._accepted_digests.add(envelope.digest())

    def last_sequence(self, session_id: str, direction: ChannelDirection, purpose: ChannelPurpose) -> int:
        return self._last_sequence.get((session_id, direction, purpose), 0)


class SecureChannel:
    """Verifies signed node/controller envelopes against node sessions."""

    def __init__(
        self,
        *,
        registry: Any | None = None,
        replay_guard: ReplayGuard | None = None,
        max_clock_skew_seconds: int = 60,
        max_message_age_seconds: int = 300,
    ) -> None:
        if max_clock_skew_seconds < 0:
            raise SecureChannelError("max_clock_skew_seconds must be >= 0")
        if max_message_age_seconds <= 0:
            raise SecureChannelError("max_message_age_seconds must be positive")
        self.registry = registry
        self.replay_guard = replay_guard or ReplayGuard()
        self.max_clock_skew_seconds = max_clock_skew_seconds
        self.max_message_age_seconds = max_message_age_seconds
        self.journal: list[ChannelVerification] = []

    def build_envelope(
        self,
        *,
        node_id: str,
        session_id: str,
        direction: ChannelDirection,
        purpose: ChannelPurpose,
        sequence: int,
        payload: Mapping[str, Any],
        session_token: str,
        issued_at: datetime | None = None,
        ttl_seconds: int | None = 300,
        correlation_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SignedChannelEnvelope:
        current = issued_at or _now()
        expires_at = current + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        envelope = SignedChannelEnvelope(
            node_id=node_id,
            session_id=session_id,
            direction=direction,
            purpose=purpose,
            sequence=sequence,
            payload=payload,
            issued_at=current,
            expires_at=expires_at,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        return envelope.sign(session_token)

    def verify(
        self,
        envelope: SignedChannelEnvelope,
        *,
        session_token: str,
        expected_direction: ChannelDirection | None = None,
        expected_purpose: ChannelPurpose | None = None,
        now: datetime | None = None,
    ) -> ChannelVerification:
        current = now or _now()
        if expected_direction is not None and envelope.direction != expected_direction:
            return self._record(envelope, ChannelDecision.DENY, "unexpected message direction", ("direction-mismatch",))
        if expected_purpose is not None and envelope.purpose != expected_purpose:
            return self._record(envelope, ChannelDecision.DENY, "unexpected message purpose", ("purpose-mismatch",))
        if envelope.issued_at > current + timedelta(seconds=self.max_clock_skew_seconds):
            return self._record(envelope, ChannelDecision.DENY, "message timestamp is too far in the future", ("clock-skew",))
        if (current - envelope.issued_at).total_seconds() > self.max_message_age_seconds:
            return self._record(envelope, ChannelDecision.STALE, "message is older than allowed age", ("stale-message",))
        if envelope.expires_at is not None and envelope.expires_at <= current:
            return self._record(envelope, ChannelDecision.STALE, "message expired", ("expired-message",))
        if self.registry is not None and hasattr(self.registry, "verify_session"):
            if not self.registry.verify_session(envelope.session_id, envelope.node_id, session_token):
                return self._record(envelope, ChannelDecision.DENY, "session verification failed", ("invalid-session",))
        if not envelope.verify_signature(session_token):
            return self._record(envelope, ChannelDecision.DENY, "signature verification failed", ("invalid-signature",))
        replay = self.replay_guard.check(envelope)
        if replay is not None:
            return self._append(replay)
        self.replay_guard.accept(envelope)
        return self._record(envelope, ChannelDecision.ACCEPT, "message accepted", ())

    def _record(
        self,
        envelope: SignedChannelEnvelope,
        status: ChannelDecision,
        reason: str,
        findings: tuple[str, ...],
    ) -> ChannelVerification:
        return self._append(
            ChannelVerification(
                status=status,
                envelope_id=envelope.id,
                node_id=envelope.node_id,
                reason=reason,
                findings=findings,
            )
        )

    def _append(self, verification: ChannelVerification) -> ChannelVerification:
        self.journal.append(verification)
        return verification


class SecureChannelRouter:
    """Optional adapter that routes verified envelopes to local MVP components."""

    def __init__(
        self,
        *,
        channel: SecureChannel,
        heartbeat_store: Any | None = None,
        action_dispatcher: Any | None = None,
    ) -> None:
        self.channel = channel
        self.heartbeat_store = heartbeat_store
        self.action_dispatcher = action_dispatcher
        self.dispatch_journal: list[dict[str, Any]] = []

    def ingest_heartbeat(
        self,
        envelope: SignedChannelEnvelope,
        *,
        session_token: str,
        now: datetime | None = None,
    ) -> tuple[ChannelVerification, Any | None]:
        decision = self.channel.verify(
            envelope,
            session_token=session_token,
            expected_direction=ChannelDirection.NODE_TO_CONTROLLER,
            expected_purpose=ChannelPurpose.HEARTBEAT,
            now=now,
        )
        if not decision.accepted:
            self.dispatch_journal.append({"envelope_id": envelope.id, "action": "heartbeat.denied", "reason": decision.reason})
            return decision, None
        if self.heartbeat_store is None or NodeHeartbeat is None:
            self.dispatch_journal.append({"envelope_id": envelope.id, "action": "heartbeat.accepted.no_store"})
            return decision, None
        payload = dict(envelope.payload)
        metrics = dict(payload.get("metrics", {}))
        heartbeat = NodeHeartbeat.from_metrics(
            node_id=envelope.node_id,
            sequence=int(payload.get("sequence", envelope.sequence)),
            session_id=envelope.session_id,
            metrics=metrics,
            capabilities=payload.get("capabilities", ()),
            labels=payload.get("labels", {}),
            data_locality=payload.get("data_locality", ()),
            metadata={"secure_envelope_id": envelope.id, **dict(payload.get("metadata", {}))},
            observed_at=envelope.issued_at,
        )
        result = self.heartbeat_store.ingest(heartbeat, session_token=session_token, now=now) if hasattr(self.heartbeat_store, "ingest") else None
        self.dispatch_journal.append({"envelope_id": envelope.id, "action": "heartbeat.ingested", "result": str(result)})
        return decision, result

    def dispatch_action(
        self,
        envelope: SignedChannelEnvelope,
        *,
        session_token: str,
        now: datetime | None = None,
    ) -> tuple[ChannelVerification, Any | None]:
        decision = self.channel.verify(
            envelope,
            session_token=session_token,
            expected_direction=ChannelDirection.CONTROLLER_TO_NODE,
            expected_purpose=ChannelPurpose.ACTION,
            now=now,
        )
        if not decision.accepted:
            self.dispatch_journal.append({"envelope_id": envelope.id, "action": "node_action.denied", "reason": decision.reason})
            return decision, None
        if self.action_dispatcher is None or AgentActionRequest is None:
            self.dispatch_journal.append({"envelope_id": envelope.id, "action": "node_action.accepted.no_dispatcher"})
            return decision, None
        payload = dict(envelope.payload)
        request = AgentActionRequest(
            target_node=envelope.node_id,
            action=AgentActionType(payload.get("action")) if AgentActionType is not None else payload.get("action"),
            payload=payload.get("payload", {}),
            dry_run=bool(payload.get("dry_run", True)),
            approval_tokens=tuple(payload.get("approval_tokens", ())),
            requested_by=str(payload.get("requested_by", "secure-channel")),
            correlation_id=envelope.correlation_id,
        )
        result = self.action_dispatcher.registry.dispatch(request) if hasattr(self.action_dispatcher, "registry") else self.action_dispatcher.dispatch(request)
        self.dispatch_journal.append({"envelope_id": envelope.id, "action": "node_action.dispatched", "result": result.status.value})
        return decision, result
