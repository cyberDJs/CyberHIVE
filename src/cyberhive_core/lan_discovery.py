"""CyberHIVE LAN Discovery & Enrollment Handshake MVP.

This module models safe local-network discovery without opening sockets.

Discovery is intentionally untrusted. A discovered node is only a candidate
until it completes the enrollment proof from node_identity. This MVP provides:

* structured LAN advertisements,
* private/local address validation,
* discovery registry with TTL and stale detection,
* enrollment handshake challenges,
* HMAC-backed enrollment completion through EnrollmentAuthority,
* optional capability filtering before enrollment.

It does not implement mDNS, UDP multicast, QR provisioning, mTLS, SSH or remote
execution. Those should plug into these contracts later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import ipaddress
from typing import Any, Iterable, Mapping
import uuid

from .node_identity import (
    EnrollmentAuthority,
    EnrollmentDecision,
    EnrollmentRequest,
    EnrollmentStatus,
    compute_enrollment_proof,
)


class DiscoverySource(str, Enum):
    LAN_BROADCAST = "lan_broadcast"
    MDNS = "mdns"
    STATIC_HINT = "static_hint"
    MANUAL = "manual"


class DiscoveryStatus(str, Enum):
    SEEN = "seen"
    STALE = "stale"
    REJECTED = "rejected"
    HANDSHAKE_READY = "handshake_ready"
    ENROLLED = "enrolled"


class HandshakeStatus(str, Enum):
    ISSUED = "issued"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class LANDiscoveryError(RuntimeError):
    """Raised when LAN discovery or handshake input is invalid."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _normalize_endpoint(endpoint: str) -> str:
    if not endpoint or not endpoint.strip():
        raise LANDiscoveryError("endpoint is required")
    return endpoint.strip()


def _endpoint_host(endpoint: str) -> str:
    value = _normalize_endpoint(endpoint)
    if "://" in value:
        value = value.split("://", 1)[1]
    if "/" in value:
        value = value.split("/", 1)[0]
    if value.startswith("[") and "]" in value:
        return value[1 : value.index("]")]
    if ":" in value:
        return value.rsplit(":", 1)[0]
    return value


def is_lan_address(endpoint: str) -> bool:
    """Return True when an endpoint host is private/link-local/loopback.

    Hostnames ending in .local or without dots are accepted as local discovery
    names. Public IPs and fully-qualified external DNS names are rejected.
    """

    host = _endpoint_host(endpoint).strip().lower()
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host.endswith(".local") or "." not in host
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local)


def _sanitize_capabilities(values: Iterable[str]) -> tuple[str, ...]:
    capabilities = tuple(sorted({str(item).strip() for item in values if str(item).strip()}))
    if any(" " in item for item in capabilities):
        raise LANDiscoveryError("capabilities must not contain spaces")
    return capabilities


@dataclass(frozen=True)
class NodeAdvertisement:
    """Unauthenticated node presence announcement.

    A NodeAdvertisement is not an identity. It only says that something on the
    local network claims to be a CyberHIVE-capable node.
    """

    proposed_node_id: str
    endpoints: tuple[str, ...]
    capabilities: tuple[str, ...] = ()
    source: DiscoverySource = DiscoverySource.LAN_BROADCAST
    labels: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    public_key_hint: str | None = None
    observed_at: datetime = field(default_factory=_now)
    id: str = field(default_factory=lambda: f"adv_{uuid.uuid4().hex[:20]}")

    def __post_init__(self) -> None:
        if not self.proposed_node_id or not self.proposed_node_id.strip():
            raise LANDiscoveryError("proposed_node_id is required")
        if self.observed_at.tzinfo is None:
            raise LANDiscoveryError("observed_at must be timezone-aware")
        endpoints = tuple(_normalize_endpoint(item) for item in self.endpoints)
        if not endpoints:
            raise LANDiscoveryError("at least one endpoint is required")
        object.__setattr__(self, "endpoints", endpoints)
        object.__setattr__(self, "capabilities", _sanitize_capabilities(self.capabilities))

    @property
    def lan_safe(self) -> bool:
        return all(is_lan_address(endpoint) for endpoint in self.endpoints)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "proposed_node_id": self.proposed_node_id,
            "endpoints": list(self.endpoints),
            "capabilities": list(self.capabilities),
            "source": self.source.value,
            "labels": dict(self.labels),
            "metadata": dict(self.metadata),
            "public_key_hint": self.public_key_hint,
            "observed_at": self.observed_at.isoformat(),
            "lan_safe": self.lan_safe,
        }


@dataclass(frozen=True)
class DiscoveryRecord:
    advertisement: NodeAdvertisement
    status: DiscoveryStatus
    reason: str
    first_seen_at: datetime
    last_seen_at: datetime
    seen_count: int = 1
    findings: tuple[str, ...] = ()
    handshake_id: str | None = None
    enrolled_identity_id: str | None = None

    @property
    def proposed_node_id(self) -> str:
        return self.advertisement.proposed_node_id

    def stale(self, *, ttl_seconds: int, now: datetime | None = None) -> bool:
        return ((now or _now()) - self.last_seen_at).total_seconds() >= ttl_seconds

    def as_dict(self) -> dict[str, Any]:
        return {
            "advertisement": self.advertisement.as_dict(),
            "status": self.status.value,
            "reason": self.reason,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "seen_count": self.seen_count,
            "findings": list(self.findings),
            "handshake_id": self.handshake_id,
            "enrolled_identity_id": self.enrolled_identity_id,
        }


class LANDiscoveryRegistry:
    """In-memory registry of untrusted LAN advertisements."""

    def __init__(self, *, ttl_seconds: int = 120, allow_public_endpoints: bool = False) -> None:
        if ttl_seconds <= 0:
            raise LANDiscoveryError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self.allow_public_endpoints = allow_public_endpoints
        self._records: dict[str, DiscoveryRecord] = {}
        self.journal: list[DiscoveryRecord] = []

    def observe(self, advertisement: NodeAdvertisement, *, now: datetime | None = None) -> DiscoveryRecord:
        current = now or _now()
        findings: list[str] = []
        if advertisement.observed_at > current + timedelta(seconds=30):
            record = DiscoveryRecord(
                advertisement=advertisement,
                status=DiscoveryStatus.REJECTED,
                reason="advertisement timestamp is too far in the future",
                first_seen_at=current,
                last_seen_at=current,
                findings=("clock-skew",),
            )
            return self._record(record)
        if not advertisement.lan_safe and not self.allow_public_endpoints:
            record = DiscoveryRecord(
                advertisement=advertisement,
                status=DiscoveryStatus.REJECTED,
                reason="advertisement contains non-LAN endpoint",
                first_seen_at=current,
                last_seen_at=current,
                findings=("public-endpoint-rejected",),
            )
            return self._record(record)
        if not advertisement.capabilities:
            findings.append("advertisement declares no capabilities")
        previous = self._records.get(advertisement.proposed_node_id)
        if previous:
            record = DiscoveryRecord(
                advertisement=advertisement,
                status=DiscoveryStatus.SEEN,
                reason="advertisement refreshed",
                first_seen_at=previous.first_seen_at,
                last_seen_at=current,
                seen_count=previous.seen_count + 1,
                findings=tuple(findings),
                handshake_id=previous.handshake_id,
                enrolled_identity_id=previous.enrolled_identity_id,
            )
        else:
            record = DiscoveryRecord(
                advertisement=advertisement,
                status=DiscoveryStatus.SEEN,
                reason="advertisement observed",
                first_seen_at=current,
                last_seen_at=current,
                findings=tuple(findings),
            )
        self._records[advertisement.proposed_node_id] = record
        return self._record(record)

    def get(self, proposed_node_id: str) -> DiscoveryRecord | None:
        return self._records.get(proposed_node_id)

    def require(self, proposed_node_id: str) -> DiscoveryRecord:
        record = self.get(proposed_node_id)
        if record is None:
            raise LANDiscoveryError(f"unknown discovered node: {proposed_node_id}")
        return record

    def mark_handshake_ready(self, proposed_node_id: str, handshake_id: str) -> DiscoveryRecord:
        record = self.require(proposed_node_id)
        updated = DiscoveryRecord(
            advertisement=record.advertisement,
            status=DiscoveryStatus.HANDSHAKE_READY,
            reason="enrollment handshake issued",
            first_seen_at=record.first_seen_at,
            last_seen_at=record.last_seen_at,
            seen_count=record.seen_count,
            findings=record.findings,
            handshake_id=handshake_id,
            enrolled_identity_id=record.enrolled_identity_id,
        )
        self._records[proposed_node_id] = updated
        return self._record(updated)

    def mark_enrolled(self, proposed_node_id: str, identity_id: str) -> DiscoveryRecord:
        record = self.require(proposed_node_id)
        updated = DiscoveryRecord(
            advertisement=record.advertisement,
            status=DiscoveryStatus.ENROLLED,
            reason="node enrolled from LAN discovery",
            first_seen_at=record.first_seen_at,
            last_seen_at=record.last_seen_at,
            seen_count=record.seen_count,
            findings=record.findings,
            handshake_id=record.handshake_id,
            enrolled_identity_id=identity_id,
        )
        self._records[proposed_node_id] = updated
        return self._record(updated)

    def list_records(self, *, include_rejected: bool = False, now: datetime | None = None) -> tuple[DiscoveryRecord, ...]:
        records: list[DiscoveryRecord] = []
        for record in self._records.values():
            if record.status == DiscoveryStatus.REJECTED and not include_rejected:
                continue
            if record.stale(ttl_seconds=self.ttl_seconds, now=now) and record.status == DiscoveryStatus.SEEN:
                records.append(
                    DiscoveryRecord(
                        advertisement=record.advertisement,
                        status=DiscoveryStatus.STALE,
                        reason="advertisement stale",
                        first_seen_at=record.first_seen_at,
                        last_seen_at=record.last_seen_at,
                        seen_count=record.seen_count,
                        findings=record.findings,
                        handshake_id=record.handshake_id,
                        enrolled_identity_id=record.enrolled_identity_id,
                    )
                )
            else:
                records.append(record)
        return tuple(sorted(records, key=lambda item: item.proposed_node_id))

    def _record(self, record: DiscoveryRecord) -> DiscoveryRecord:
        self.journal.append(record)
        return record


@dataclass(frozen=True)
class EnrollmentHandshake:
    id: str
    proposed_node_id: str
    bootstrap_token_id: str
    bootstrap_secret: str
    allowed_capabilities: tuple[str, ...]
    endpoints: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    status: HandshakeStatus = HandshakeStatus.ISSUED
    reason: str = "handshake issued"
    discovery_record_id: str | None = None
    enrollment_request_id: str | None = None
    identity_id: str | None = None

    def is_active(self, now: datetime | None = None) -> bool:
        return self.status == HandshakeStatus.ISSUED and self.expires_at > (now or _now())

    def public_challenge(self) -> dict[str, Any]:
        """Public challenge material safe to show to an operator or node.

        The bootstrap_secret is intentionally omitted. In a real deployment it
        should be delivered through a separate local-only channel or QR code.
        """

        return {
            "id": self.id,
            "proposed_node_id": self.proposed_node_id,
            "bootstrap_token_id": self.bootstrap_token_id,
            "allowed_capabilities": list(self.allowed_capabilities),
            "endpoints": list(self.endpoints),
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
        }

    def as_dict(self, *, include_secret: bool = False) -> dict[str, Any]:
        data = self.public_challenge()
        data.update(
            {
                "reason": self.reason,
                "discovery_record_id": self.discovery_record_id,
                "enrollment_request_id": self.enrollment_request_id,
                "identity_id": self.identity_id,
            }
        )
        if include_secret:
            data["bootstrap_secret"] = self.bootstrap_secret
        return data


@dataclass(frozen=True)
class HandshakeResponse:
    handshake_id: str
    proposed_node_id: str
    public_key: str
    nonce: str
    proof: str
    capabilities: tuple[str, ...]
    labels: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"hres_{uuid.uuid4().hex[:20]}")

    @classmethod
    def sign(
        cls,
        *,
        handshake: EnrollmentHandshake,
        public_key: str,
        nonce: str,
        capabilities: Iterable[str] = (),
        labels: Mapping[str, str] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "HandshakeResponse":
        requested_capabilities = _sanitize_capabilities(capabilities)
        proof = compute_enrollment_proof(
            handshake.proposed_node_id,
            public_key,
            nonce,
            handshake.bootstrap_token_id,
            handshake.bootstrap_secret,
        )
        return cls(
            handshake_id=handshake.id,
            proposed_node_id=handshake.proposed_node_id,
            public_key=public_key,
            nonce=nonce,
            proof=proof,
            capabilities=requested_capabilities,
            labels=labels or {},
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "handshake_id": self.handshake_id,
            "proposed_node_id": self.proposed_node_id,
            "nonce": self.nonce,
            "capabilities": list(self.capabilities),
            "labels": dict(self.labels),
            "metadata": dict(self.metadata),
        }


class LANEnrollmentCoordinator:
    """Coordinates discovery records with node enrollment authority."""

    def __init__(
        self,
        *,
        discovery: LANDiscoveryRegistry | None = None,
        authority: EnrollmentAuthority | None = None,
        handshake_ttl_seconds: int = 300,
    ) -> None:
        if handshake_ttl_seconds <= 0:
            raise LANDiscoveryError("handshake_ttl_seconds must be positive")
        self.discovery = discovery or LANDiscoveryRegistry()
        self.authority = authority or EnrollmentAuthority()
        self.handshake_ttl_seconds = handshake_ttl_seconds
        self._handshakes: dict[str, EnrollmentHandshake] = {}

    def issue_handshake(
        self,
        proposed_node_id: str,
        *,
        allowed_capabilities: Iterable[str] | None = None,
        now: datetime | None = None,
    ) -> EnrollmentHandshake:
        current = now or _now()
        record = self.discovery.require(proposed_node_id)
        if record.status == DiscoveryStatus.REJECTED:
            raise LANDiscoveryError("cannot issue handshake for rejected discovery record")
        if record.stale(ttl_seconds=self.discovery.ttl_seconds, now=current):
            raise LANDiscoveryError("cannot issue handshake for stale discovery record")
        discovered = set(record.advertisement.capabilities)
        requested = set(_sanitize_capabilities(allowed_capabilities if allowed_capabilities is not None else discovered))
        if discovered and not requested.issubset(discovered):
            raise LANDiscoveryError("allowed capabilities exceed advertised capabilities")
        token, secret = self.authority.create_bootstrap_token(ttl_seconds=self.handshake_ttl_seconds, max_uses=1)
        handshake = EnrollmentHandshake(
            id=f"hs_{uuid.uuid4().hex[:20]}",
            proposed_node_id=proposed_node_id,
            bootstrap_token_id=token.id,
            bootstrap_secret=secret,
            allowed_capabilities=tuple(sorted(requested)),
            endpoints=record.advertisement.endpoints,
            issued_at=current,
            expires_at=current + timedelta(seconds=self.handshake_ttl_seconds),
            discovery_record_id=record.advertisement.id,
        )
        self._handshakes[handshake.id] = handshake
        self.discovery.mark_handshake_ready(proposed_node_id, handshake.id)
        return handshake

    def get_handshake(self, handshake_id: str) -> EnrollmentHandshake | None:
        return self._handshakes.get(handshake_id)

    def require_handshake(self, handshake_id: str) -> EnrollmentHandshake:
        handshake = self.get_handshake(handshake_id)
        if handshake is None:
            raise LANDiscoveryError(f"unknown handshake: {handshake_id}")
        return handshake

    def complete_handshake(self, response: HandshakeResponse, *, now: datetime | None = None) -> EnrollmentDecision:
        current = now or _now()
        handshake = self.require_handshake(response.handshake_id)
        if not handshake.is_active(current):
            expired = EnrollmentHandshake(
                **{**handshake.__dict__, "status": HandshakeStatus.EXPIRED, "reason": "handshake expired"}
            )
            self._handshakes[handshake.id] = expired
            return EnrollmentDecision(EnrollmentStatus.DENIED, response.id, "handshake expired")
        if response.proposed_node_id != handshake.proposed_node_id:
            return EnrollmentDecision(EnrollmentStatus.DENIED, response.id, "handshake node id mismatch")
        requested = set(response.capabilities)
        allowed = set(handshake.allowed_capabilities)
        if requested and not requested.issubset(allowed):
            return EnrollmentDecision(EnrollmentStatus.DENIED, response.id, "response capabilities exceed handshake allowance")
        request = EnrollmentRequest(
            proposed_node_id=response.proposed_node_id,
            public_key=response.public_key,
            bootstrap_token_id=handshake.bootstrap_token_id,
            nonce=response.nonce,
            proof=response.proof,
            capabilities=tuple(sorted(requested or allowed)),
            labels=dict(response.labels),
            metadata={**dict(response.metadata), "handshake_id": handshake.id, "discovery_record_id": handshake.discovery_record_id},
            requested_by="lan-discovery",
        )
        decision = self.authority.evaluate(request)
        if decision.approved and decision.identity:
            status = HandshakeStatus.APPROVED
            reason = "handshake completed"
            identity_id = decision.identity.id
            self.discovery.mark_enrolled(response.proposed_node_id, identity_id)
        else:
            status = HandshakeStatus.DENIED
            reason = decision.reason
            identity_id = None
        updated = EnrollmentHandshake(
            **{
                **handshake.__dict__,
                "status": status,
                "reason": reason,
                "enrollment_request_id": request.id,
                "identity_id": identity_id,
            }
        )
        self._handshakes[handshake.id] = updated
        return decision

    def list_handshakes(self) -> tuple[EnrollmentHandshake, ...]:
        return tuple(sorted(self._handshakes.values(), key=lambda item: item.issued_at))
