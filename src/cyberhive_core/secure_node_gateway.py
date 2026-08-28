"""CyberHIVE Secure Node Gateway MVP.

Controller/node message ingress and egress on top of Secure Channel.

Patch 017 introduced signed envelopes. This patch adds a small gateway layer
that owns in-memory session credentials, routes verified envelopes to the
heartbeat/action surfaces, records receipts, and can build signed controller
messages without passing raw session tokens through every caller.

The MVP intentionally does not open sockets, persist secrets, implement TLS,
start daemons, or execute shell commands. It is an integration boundary only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
import uuid

from .secure_channel import (
    ChannelDecision,
    ChannelDirection,
    ChannelPurpose,
    ChannelVerification,
    SecureChannel,
    SecureChannelRouter,
    SignedChannelEnvelope,
)


class SecureNodeGatewayError(RuntimeError):
    """Raised when the secure node gateway cannot process a request."""


class GatewayMessageStatus(str, Enum):
    ACCEPTED = "accepted"
    DENIED = "denied"
    DISPATCHED = "dispatched"
    RECORDED = "recorded"
    ERROR = "error"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SessionCredential:
    """In-memory session secret held by the gateway.

    The MVP keeps the token in memory only. A later secret-store patch should
    replace this with OS keychain / sealed storage / KMS-backed retrieval.
    """

    session_id: str
    node_id: str
    token: str
    created_at: datetime = field(default_factory=_now)
    expires_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    revoked: bool = False

    def active(self, now: datetime | None = None) -> bool:
        current = now or _now()
        if self.revoked:
            return False
        if self.expires_at is not None and self.expires_at <= current:
            return False
        return True

    def as_dict(self, *, include_secret: bool = False) -> dict[str, Any]:
        data = {
            "session_id": self.session_id,
            "node_id": self.node_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": dict(self.metadata),
            "revoked": self.revoked,
        }
        if include_secret:
            data["token"] = self.token
        else:
            data["token"] = "<redacted>"
        return data


class SessionCredentialVault:
    """Minimal in-memory credential vault for node session tokens."""

    def __init__(self) -> None:
        self._by_session: dict[str, SessionCredential] = {}

    def store(
        self,
        *,
        session_id: str,
        node_id: str,
        token: str,
        expires_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SessionCredential:
        if not session_id:
            raise SecureNodeGatewayError("session_id is required")
        if not node_id:
            raise SecureNodeGatewayError("node_id is required")
        if not token:
            raise SecureNodeGatewayError("token is required")
        existing = self._by_session.get(session_id)
        if existing is not None and existing.node_id != node_id:
            raise SecureNodeGatewayError("session_id is already assigned to another node")
        credential = SessionCredential(
            session_id=session_id,
            node_id=node_id,
            token=token,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        self._by_session[session_id] = credential
        return credential

    def get(self, session_id: str) -> SessionCredential | None:
        return self._by_session.get(session_id)

    def require(self, session_id: str, node_id: str | None = None, now: datetime | None = None) -> SessionCredential:
        credential = self.get(session_id)
        if credential is None:
            raise SecureNodeGatewayError("no session credential available")
        if node_id is not None and credential.node_id != node_id:
            raise SecureNodeGatewayError("session credential belongs to a different node")
        if not credential.active(now=now):
            raise SecureNodeGatewayError("session credential is not active")
        return credential

    def revoke(self, session_id: str) -> SessionCredential:
        credential = self.require(session_id)
        revoked = SessionCredential(
            session_id=credential.session_id,
            node_id=credential.node_id,
            token=credential.token,
            created_at=credential.created_at,
            expires_at=credential.expires_at,
            metadata=credential.metadata,
            revoked=True,
        )
        self._by_session[session_id] = revoked
        return revoked

    def forget(self, session_id: str) -> bool:
        return self._by_session.pop(session_id, None) is not None

    def list_credentials(self) -> tuple[SessionCredential, ...]:
        return tuple(self._by_session.values())


@dataclass(frozen=True)
class GatewayReceipt:
    """Auditable outcome for a secure gateway message."""

    status: GatewayMessageStatus
    envelope_id: str
    node_id: str
    purpose: ChannelPurpose
    direction: ChannelDirection
    reason: str
    verification: ChannelVerification | None = None
    result: Any | None = None
    created_at: datetime = field(default_factory=_now)
    id: str = field(default_factory=lambda: f"gw_{uuid.uuid4().hex[:20]}")

    @property
    def ok(self) -> bool:
        return self.status in {
            GatewayMessageStatus.ACCEPTED,
            GatewayMessageStatus.DISPATCHED,
            GatewayMessageStatus.RECORDED,
        }

    def as_dict(self) -> dict[str, Any]:
        result = self.result
        if hasattr(result, "as_dict"):
            result_payload = result.as_dict()
        elif hasattr(result, "value"):
            result_payload = result.value
        else:
            result_payload = result
        return {
            "id": self.id,
            "status": self.status.value,
            "envelope_id": self.envelope_id,
            "node_id": self.node_id,
            "purpose": self.purpose.value,
            "direction": self.direction.value,
            "reason": self.reason,
            "verification": None if self.verification is None else self.verification.as_dict(),
            "result": result_payload,
            "created_at": self.created_at.isoformat(),
        }


class SecureNodeGateway:
    """Gateway that combines credential lookup, verification and local routing."""

    def __init__(
        self,
        *,
        channel: SecureChannel,
        credential_vault: SessionCredentialVault | None = None,
        heartbeat_store: Any | None = None,
        action_dispatcher: Any | None = None,
    ) -> None:
        self.channel = channel
        self.credential_vault = credential_vault or SessionCredentialVault()
        self.router = SecureChannelRouter(
            channel=channel,
            heartbeat_store=heartbeat_store,
            action_dispatcher=action_dispatcher,
        )
        self.receipts: list[GatewayReceipt] = []
        self.inbox: list[SignedChannelEnvelope] = []
        self.outbox: list[SignedChannelEnvelope] = []
        self.action_results: list[Mapping[str, Any]] = []
        self.acks: list[Mapping[str, Any]] = []
        self.errors: list[Mapping[str, Any]] = []
        self._next_sequence: dict[tuple[str, ChannelDirection, ChannelPurpose], int] = {}

    def store_session(self, *, session_id: str, node_id: str, token: str, expires_at: datetime | None = None) -> SessionCredential:
        return self.credential_vault.store(session_id=session_id, node_id=node_id, token=token, expires_at=expires_at)

    def next_sequence(self, session_id: str, direction: ChannelDirection, purpose: ChannelPurpose) -> int:
        key = (session_id, direction, purpose)
        value = self._next_sequence.get(key, 0) + 1
        self._next_sequence[key] = value
        return value

    def build_action_envelope(
        self,
        *,
        node_id: str,
        session_id: str,
        action: str,
        payload: Mapping[str, Any] | None = None,
        dry_run: bool = True,
        approval_tokens: tuple[str, ...] = (),
        requested_by: str = "secure-node-gateway",
        sequence: int | None = None,
        correlation_id: str | None = None,
        ttl_seconds: int | None = 300,
    ) -> SignedChannelEnvelope:
        credential = self.credential_vault.require(session_id, node_id)
        envelope = self.channel.build_envelope(
            node_id=node_id,
            session_id=session_id,
            direction=ChannelDirection.CONTROLLER_TO_NODE,
            purpose=ChannelPurpose.ACTION,
            sequence=sequence or self.next_sequence(session_id, ChannelDirection.CONTROLLER_TO_NODE, ChannelPurpose.ACTION),
            payload={
                "action": action,
                "payload": dict(payload or {}),
                "dry_run": dry_run,
                "approval_tokens": list(approval_tokens),
                "requested_by": requested_by,
            },
            session_token=credential.token,
            correlation_id=correlation_id,
            ttl_seconds=ttl_seconds,
        )
        self.outbox.append(envelope)
        return envelope

    def build_ack_envelope(
        self,
        *,
        node_id: str,
        session_id: str,
        correlation_id: str | None,
        payload: Mapping[str, Any] | None = None,
        sequence: int | None = None,
    ) -> SignedChannelEnvelope:
        credential = self.credential_vault.require(session_id, node_id)
        envelope = self.channel.build_envelope(
            node_id=node_id,
            session_id=session_id,
            direction=ChannelDirection.CONTROLLER_TO_NODE,
            purpose=ChannelPurpose.ACK,
            sequence=sequence or self.next_sequence(session_id, ChannelDirection.CONTROLLER_TO_NODE, ChannelPurpose.ACK),
            payload=dict(payload or {}),
            session_token=credential.token,
            correlation_id=correlation_id,
        )
        self.outbox.append(envelope)
        return envelope

    def receive(self, envelope: SignedChannelEnvelope, *, now: datetime | None = None) -> GatewayReceipt:
        self.inbox.append(envelope)
        try:
            credential = self.credential_vault.require(envelope.session_id, envelope.node_id, now=now)
        except SecureNodeGatewayError as exc:
            return self._record(
                GatewayReceipt(
                    status=GatewayMessageStatus.DENIED,
                    envelope_id=envelope.id,
                    node_id=envelope.node_id,
                    purpose=envelope.purpose,
                    direction=envelope.direction,
                    reason=str(exc),
                )
            )

        if envelope.direction == ChannelDirection.NODE_TO_CONTROLLER and envelope.purpose == ChannelPurpose.HEARTBEAT:
            decision, result = self.router.ingest_heartbeat(envelope, session_token=credential.token, now=now)
            return self._from_verification(decision, result=result, success_status=GatewayMessageStatus.DISPATCHED, success_reason="heartbeat ingested")

        if envelope.direction == ChannelDirection.CONTROLLER_TO_NODE and envelope.purpose == ChannelPurpose.ACTION:
            decision, result = self.router.dispatch_action(envelope, session_token=credential.token, now=now)
            return self._from_verification(decision, result=result, success_status=GatewayMessageStatus.DISPATCHED, success_reason="action dispatched")

        if envelope.direction == ChannelDirection.NODE_TO_CONTROLLER and envelope.purpose == ChannelPurpose.ACTION_RESULT:
            decision = self.channel.verify(
                envelope,
                session_token=credential.token,
                expected_direction=ChannelDirection.NODE_TO_CONTROLLER,
                expected_purpose=ChannelPurpose.ACTION_RESULT,
                now=now,
            )
            if decision.accepted:
                self.action_results.append(dict(envelope.payload))
            return self._from_verification(decision, result=dict(envelope.payload), success_status=GatewayMessageStatus.RECORDED, success_reason="action result recorded")

        if envelope.purpose == ChannelPurpose.ACK:
            decision = self.channel.verify(envelope, session_token=credential.token, expected_purpose=ChannelPurpose.ACK, now=now)
            if decision.accepted:
                self.acks.append(dict(envelope.payload))
            return self._from_verification(decision, result=dict(envelope.payload), success_status=GatewayMessageStatus.RECORDED, success_reason="ack recorded")

        if envelope.purpose == ChannelPurpose.ERROR:
            decision = self.channel.verify(envelope, session_token=credential.token, expected_purpose=ChannelPurpose.ERROR, now=now)
            if decision.accepted:
                self.errors.append(dict(envelope.payload))
            return self._from_verification(decision, result=dict(envelope.payload), success_status=GatewayMessageStatus.RECORDED, success_reason="error recorded")

        verification = ChannelVerification(
            status=ChannelDecision.DENY,
            envelope_id=envelope.id,
            node_id=envelope.node_id,
            reason="unsupported direction/purpose for secure node gateway",
            findings=("unsupported-gateway-message",),
        )
        return self._from_verification(verification, result=None, success_status=GatewayMessageStatus.ACCEPTED, success_reason="message accepted")

    def _from_verification(
        self,
        verification: ChannelVerification,
        *,
        result: Any | None,
        success_status: GatewayMessageStatus,
        success_reason: str,
    ) -> GatewayReceipt:
        if verification.accepted:
            status = success_status
            reason = success_reason
        elif verification.status == ChannelDecision.DUPLICATE:
            status = GatewayMessageStatus.DENIED
            reason = verification.reason
        elif verification.status == ChannelDecision.STALE:
            status = GatewayMessageStatus.DENIED
            reason = verification.reason
        else:
            status = GatewayMessageStatus.DENIED
            reason = verification.reason
        return self._record(
            GatewayReceipt(
                status=status,
                envelope_id=verification.envelope_id,
                node_id=verification.node_id,
                purpose=self._purpose_from_verification(verification),
                direction=self._direction_from_verification(verification),
                reason=reason,
                verification=verification,
                result=result,
            )
        )

    def _purpose_from_verification(self, verification: ChannelVerification) -> ChannelPurpose:
        for envelope in reversed(self.inbox + self.outbox):
            if envelope.id == verification.envelope_id:
                return envelope.purpose
        return ChannelPurpose.ERROR

    def _direction_from_verification(self, verification: ChannelVerification) -> ChannelDirection:
        for envelope in reversed(self.inbox + self.outbox):
            if envelope.id == verification.envelope_id:
                return envelope.direction
        return ChannelDirection.NODE_TO_CONTROLLER

    def _record(self, receipt: GatewayReceipt) -> GatewayReceipt:
        self.receipts.append(receipt)
        return receipt
