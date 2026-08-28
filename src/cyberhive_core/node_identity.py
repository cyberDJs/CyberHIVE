"""CyberHIVE Node Enrollment & Identity MVP.

Safe in-memory enrollment for local CyberHIVE worker nodes.

The MVP does not implement PKI, mTLS or remote attestation. It establishes the
core contracts needed before those are introduced:

* bootstrap-token based enrollment,
* signed enrollment requests using HMAC over canonical request fields,
* stable public-key fingerprints,
* node identity registry,
* trust-state transitions,
* short-lived node session grants,
* optional conversion to Node Agent descriptors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import hmac
import secrets
from typing import Any, Mapping
import uuid


class TrustState(str, Enum):
    PENDING = "pending"
    ENROLLED = "enrolled"
    QUARANTINED = "quarantined"
    REVOKED = "revoked"


class EnrollmentStatus(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    PENDING_APPROVAL = "pending_approval"


class EnrollmentError(RuntimeError):
    """Raised when an enrollment operation is invalid."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_public_key(public_key: str) -> str:
    """Normalize a public key-like string for fingerprinting.

    This intentionally accepts simple strings in MVP tests and demos. A later
    PKI patch should replace this with strict PEM/SSH key parsing.
    """

    return "\n".join(line.strip() for line in public_key.strip().splitlines() if line.strip())


def public_key_fingerprint(public_key: str) -> str:
    normalized = normalize_public_key(public_key).encode("utf-8")
    return "sha256:" + _sha256_hex(normalized)


def canonical_enrollment_payload(node_id: str, public_key: str, nonce: str, token_id: str) -> bytes:
    payload = "\n".join(
        [
            node_id.strip(),
            public_key_fingerprint(public_key),
            nonce.strip(),
            token_id.strip(),
        ]
    )
    return payload.encode("utf-8")


def token_secret_digest(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def compute_enrollment_proof(node_id: str, public_key: str, nonce: str, token_id: str, secret: str) -> str:
    """Compute the MVP enrollment HMAC proof from a one-time secret."""

    return hmac.new(
        token_secret_digest(secret),
        canonical_enrollment_payload(node_id, public_key, nonce, token_id),
        hashlib.sha256,
    ).hexdigest()


@dataclass
class BootstrapToken:
    """One-time or limited-use enrollment token.

    The cleartext secret is returned only when the token is created. The stored
    token contains only the digest used as the HMAC key.
    """

    id: str
    secret_digest: bytes
    scopes: tuple[str, ...] = ("node.enroll",)
    expires_at: datetime = field(default_factory=lambda: _now() + timedelta(hours=1))
    max_uses: int = 1
    uses: int = 0
    created_at: datetime = field(default_factory=_now)
    revoked: bool = False

    def is_active(self, now: datetime | None = None) -> bool:
        current = now or _now()
        return (not self.revoked) and self.uses < self.max_uses and self.expires_at > current

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def verify(self, request: "EnrollmentRequest") -> bool:
        expected = hmac.new(
            self.secret_digest,
            canonical_enrollment_payload(
                request.proposed_node_id,
                request.public_key,
                request.nonce,
                request.bootstrap_token_id,
            ),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, request.proof)

    def mark_used(self) -> None:
        self.uses += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scopes": list(self.scopes),
            "expires_at": self.expires_at.isoformat(),
            "max_uses": self.max_uses,
            "uses": self.uses,
            "created_at": self.created_at.isoformat(),
            "revoked": self.revoked,
        }


@dataclass(frozen=True)
class EnrollmentRequest:
    """Request from a node asking to join the CyberHIVE fabric."""

    proposed_node_id: str
    public_key: str
    bootstrap_token_id: str
    nonce: str
    proof: str
    capabilities: tuple[str, ...] = ()
    labels: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    requested_by: str = "node"
    id: str = field(default_factory=lambda: f"enr_{uuid.uuid4().hex[:20]}")
    created_at: datetime = field(default_factory=_now)

    @property
    def fingerprint(self) -> str:
        return public_key_fingerprint(self.public_key)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "proposed_node_id": self.proposed_node_id,
            "public_key_fingerprint": self.fingerprint,
            "bootstrap_token_id": self.bootstrap_token_id,
            "nonce": self.nonce,
            "capabilities": list(self.capabilities),
            "labels": dict(self.labels),
            "metadata": dict(self.metadata),
            "requested_by": self.requested_by,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class NodeIdentity:
    """Controller-side identity record for a CyberHIVE node."""

    node_id: str
    public_key_fingerprint: str
    trust_state: TrustState = TrustState.ENROLLED
    capabilities: tuple[str, ...] = ()
    labels: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"nid_{uuid.uuid4().hex[:20]}")
    enrolled_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    revoked_at: datetime | None = None
    quarantine_reason: str | None = None

    def is_allowed(self) -> bool:
        return self.trust_state == TrustState.ENROLLED

    def revoke(self) -> None:
        self.trust_state = TrustState.REVOKED
        self.revoked_at = _now()
        self.updated_at = self.revoked_at

    def quarantine(self, reason: str) -> None:
        self.trust_state = TrustState.QUARANTINED
        self.quarantine_reason = reason
        self.updated_at = _now()

    def restore(self) -> None:
        if self.trust_state == TrustState.REVOKED:
            raise EnrollmentError("revoked identity cannot be restored")
        self.trust_state = TrustState.ENROLLED
        self.quarantine_reason = None
        self.updated_at = _now()

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "public_key_fingerprint": self.public_key_fingerprint,
            "trust_state": self.trust_state.value,
            "capabilities": list(self.capabilities),
            "labels": dict(self.labels),
            "metadata": dict(self.metadata),
            "enrolled_at": self.enrolled_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "quarantine_reason": self.quarantine_reason,
        }

    def to_node_descriptor(self):
        """Convert this identity to a Node Agent descriptor when available."""

        try:
            from .node_agent import AgentActionType, NodeDescriptor
        except Exception as exc:  # pragma: no cover
            raise EnrollmentError("node_agent module is not available") from exc

        allowed_actions: tuple[AgentActionType, ...] = (
            AgentActionType.HEALTH_CHECK,
            AgentActionType.NOOP,
        )
        if "model.prewarm" in self.capabilities:
            allowed_actions += (AgentActionType.PREWARM_MODEL,)
        if "data.move" in self.capabilities:
            allowed_actions += (AgentActionType.DATA_MOVE,)
        if "cache.prime" in self.capabilities:
            allowed_actions += (AgentActionType.CACHE_PRIME,)

        return NodeDescriptor(
            id=self.node_id,
            enabled=self.trust_state != TrustState.REVOKED,
            healthy=self.trust_state == TrustState.ENROLLED,
            capabilities=self.capabilities,
            allowed_actions=allowed_actions,
            labels=dict(self.labels),
            metadata={
                **dict(self.metadata),
                "identity_id": self.id,
                "trust_state": self.trust_state.value,
                "public_key_fingerprint": self.public_key_fingerprint,
            },
        )


@dataclass(frozen=True)
class EnrollmentDecision:
    status: EnrollmentStatus
    request_id: str
    reason: str
    identity: NodeIdentity | None = None
    required_approvals: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    decided_at: datetime = field(default_factory=_now)

    @property
    def approved(self) -> bool:
        return self.status == EnrollmentStatus.APPROVED

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "request_id": self.request_id,
            "reason": self.reason,
            "identity": self.identity.as_dict() if self.identity else None,
            "required_approvals": list(self.required_approvals),
            "findings": list(self.findings),
            "decided_at": self.decided_at.isoformat(),
        }


@dataclass(frozen=True)
class NodeSessionGrant:
    """Short-lived session grant for an enrolled node."""

    id: str
    node_id: str
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    capabilities: tuple[str, ...]
    identity_id: str

    def is_active(self, now: datetime | None = None) -> bool:
        return self.expires_at > (now or _now())

    def verify(self, token: str) -> bool:
        return self.is_active() and hmac.compare_digest(self.token_hash, _sha256_hex(token.encode("utf-8")))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "capabilities": list(self.capabilities),
            "identity_id": self.identity_id,
        }


class NodeIdentityRegistry:
    """In-memory identity registry for CyberHIVE nodes."""

    def __init__(self) -> None:
        self._by_node_id: dict[str, NodeIdentity] = {}
        self._by_fingerprint: dict[str, str] = {}
        self._sessions: dict[str, NodeSessionGrant] = {}

    def register(self, identity: NodeIdentity) -> NodeIdentity:
        existing = self._by_node_id.get(identity.node_id)
        if existing and existing.id != identity.id:
            raise EnrollmentError(f"node id already enrolled: {identity.node_id}")
        fingerprint_owner = self._by_fingerprint.get(identity.public_key_fingerprint)
        if fingerprint_owner and fingerprint_owner != identity.node_id:
            raise EnrollmentError("public key fingerprint is already enrolled for another node")
        self._by_node_id[identity.node_id] = identity
        self._by_fingerprint[identity.public_key_fingerprint] = identity.node_id
        return identity

    def get(self, node_id: str) -> NodeIdentity | None:
        return self._by_node_id.get(node_id)

    def require(self, node_id: str) -> NodeIdentity:
        identity = self.get(node_id)
        if identity is None:
            raise EnrollmentError(f"unknown node identity: {node_id}")
        return identity

    def revoke(self, node_id: str) -> NodeIdentity:
        identity = self.require(node_id)
        identity.revoke()
        self._remove_sessions_for_node(node_id)
        return identity

    def quarantine(self, node_id: str, reason: str) -> NodeIdentity:
        identity = self.require(node_id)
        identity.quarantine(reason)
        self._remove_sessions_for_node(node_id)
        return identity

    def issue_session(self, node_id: str, ttl_seconds: int = 900) -> tuple[NodeSessionGrant, str]:
        identity = self.require(node_id)
        if not identity.is_allowed():
            raise EnrollmentError(f"node is not allowed to receive a session: {node_id}")
        token = secrets.token_urlsafe(32)
        issued_at = _now()
        grant = NodeSessionGrant(
            id=f"ses_{uuid.uuid4().hex[:20]}",
            node_id=node_id,
            token_hash=_sha256_hex(token.encode("utf-8")),
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=ttl_seconds),
            capabilities=identity.capabilities,
            identity_id=identity.id,
        )
        self._sessions[grant.id] = grant
        return grant, token

    def verify_session(self, session_id: str, node_id: str, token: str) -> bool:
        grant = self._sessions.get(session_id)
        if grant is None or grant.node_id != node_id or not grant.verify(token):
            return False
        identity = self._by_node_id.get(node_id)
        return bool(identity and identity.id == grant.identity_id and identity.is_allowed())

    def _remove_sessions_for_node(self, node_id: str) -> None:
        for session_id, grant in tuple(self._sessions.items()):
            if grant.node_id == node_id:
                self._sessions.pop(session_id, None)

    def list_identities(self) -> tuple[NodeIdentity, ...]:
        return tuple(self._by_node_id.values())


class EnrollmentAuthority:
    """Issues bootstrap tokens and evaluates enrollment requests."""

    def __init__(self, registry: NodeIdentityRegistry | None = None) -> None:
        self.registry = registry or NodeIdentityRegistry()
        self._tokens: dict[str, BootstrapToken] = {}
        self.decisions: list[EnrollmentDecision] = []

    def create_bootstrap_token(
        self,
        *,
        ttl_seconds: int = 900,
        max_uses: int = 1,
        scopes: tuple[str, ...] = ("node.enroll",),
    ) -> tuple[BootstrapToken, str]:
        if ttl_seconds <= 0:
            raise EnrollmentError("ttl_seconds must be positive")
        if max_uses <= 0:
            raise EnrollmentError("max_uses must be positive")
        secret = secrets.token_urlsafe(32)
        token = BootstrapToken(
            id=f"bt_{uuid.uuid4().hex[:20]}",
            secret_digest=token_secret_digest(secret),
            scopes=scopes,
            expires_at=_now() + timedelta(seconds=ttl_seconds),
            max_uses=max_uses,
        )
        self._tokens[token.id] = token
        return token, secret

    def revoke_bootstrap_token(self, token_id: str) -> None:
        token = self._tokens.get(token_id)
        if token is None:
            raise EnrollmentError(f"unknown bootstrap token: {token_id}")
        token.revoked = True

    def build_request(
        self,
        *,
        proposed_node_id: str,
        public_key: str,
        token_id: str,
        token_secret: str,
        capabilities: tuple[str, ...] = (),
        labels: Mapping[str, str] | None = None,
        metadata: Mapping[str, Any] | None = None,
        nonce: str | None = None,
    ) -> EnrollmentRequest:
        request_nonce = nonce or secrets.token_urlsafe(16)
        proof = compute_enrollment_proof(proposed_node_id, public_key, request_nonce, token_id, token_secret)
        return EnrollmentRequest(
            proposed_node_id=proposed_node_id,
            public_key=public_key,
            bootstrap_token_id=token_id,
            nonce=request_nonce,
            proof=proof,
            capabilities=capabilities,
            labels=labels or {},
            metadata=metadata or {},
        )

    def evaluate(self, request: EnrollmentRequest) -> EnrollmentDecision:
        findings: list[str] = []
        token = self._tokens.get(request.bootstrap_token_id)
        if token is None:
            return self._record(EnrollmentDecision(EnrollmentStatus.DENIED, request.id, "unknown bootstrap token"))
        if not token.has_scope("node.enroll"):
            return self._record(EnrollmentDecision(EnrollmentStatus.DENIED, request.id, "bootstrap token lacks node.enroll scope"))
        if not token.is_active():
            return self._record(EnrollmentDecision(EnrollmentStatus.DENIED, request.id, "bootstrap token is expired, exhausted or revoked"))
        if not token.verify(request):
            return self._record(EnrollmentDecision(EnrollmentStatus.DENIED, request.id, "invalid enrollment proof"))
        if self.registry.get(request.proposed_node_id):
            return self._record(EnrollmentDecision(EnrollmentStatus.DENIED, request.id, "node id already enrolled"))
        if not request.capabilities:
            findings.append("node enrolled with no declared capabilities")

        identity = NodeIdentity(
            node_id=request.proposed_node_id,
            public_key_fingerprint=request.fingerprint,
            capabilities=request.capabilities,
            labels=dict(request.labels),
            metadata={**dict(request.metadata), "enrollment_request_id": request.id},
        )
        try:
            self.registry.register(identity)
        except EnrollmentError as exc:
            return self._record(EnrollmentDecision(EnrollmentStatus.DENIED, request.id, str(exc)))
        token.mark_used()
        return self._record(
            EnrollmentDecision(
                EnrollmentStatus.APPROVED,
                request.id,
                "node enrolled",
                identity=identity,
                findings=tuple(findings),
            )
        )

    def _record(self, decision: EnrollmentDecision) -> EnrollmentDecision:
        self.decisions.append(decision)
        return decision

    def token_status(self, token_id: str) -> Mapping[str, Any]:
        token = self._tokens.get(token_id)
        if token is None:
            raise EnrollmentError(f"unknown bootstrap token: {token_id}")
        return token.as_dict()
