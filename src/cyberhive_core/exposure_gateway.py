"""CyberHIVE Exposure Gateway MVP.

The gateway is the only approved way to publish private resources such as home
cameras, local sensors, or internal services. It never exposes a device directly;
it creates scoped, audited, expiring grants.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum

from .inventory import AccessMode, ExposureMode, InventoryItem, InventoryRegistry, Sensitivity


class ExposureDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class ExposureRequest:
    resource_id: str
    subject: str
    permissions: tuple[str, ...]
    ttl_seconds: int = 3600
    reason: str = ""
    allow_recording: bool = False
    allow_download: bool = False
    requested_exposure: ExposureMode = ExposureMode.AUTHENTICATED


@dataclass
class ExposureGrant:
    id: str
    resource_id: str
    subject: str
    permissions: tuple[str, ...]
    created_at: datetime
    expires_at: datetime
    allow_recording: bool = False
    allow_download: bool = False
    direct_device_access: bool = False
    revoked: bool = False
    audit: list[str] = field(default_factory=list)

    def is_active(self, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return not self.revoked and current < self.expires_at


@dataclass(frozen=True)
class ExposureEvaluation:
    decision: ExposureDecision
    reason: str
    grant: ExposureGrant | None = None


class ExposureGateway:
    """Policy guard for safely exposing inventory resources."""

    def __init__(self, inventory: InventoryRegistry) -> None:
        self.inventory = inventory
        self._grants: dict[str, ExposureGrant] = {}

    def create_grant(self, request: ExposureRequest) -> ExposureGrant:
        item = self.inventory.get(request.resource_id)
        evaluation = self.evaluate_request(request, item)
        if evaluation.decision == ExposureDecision.DENY:
            raise PermissionError(evaluation.reason)

        now = datetime.now(UTC)
        grant = ExposureGrant(
            id="exp_" + secrets.token_urlsafe(16),
            resource_id=request.resource_id,
            subject=request.subject,
            permissions=request.permissions,
            created_at=now,
            expires_at=now + timedelta(seconds=request.ttl_seconds),
            allow_recording=request.allow_recording,
            allow_download=request.allow_download,
            direct_device_access=False,
            audit=[f"created:{request.reason or 'no reason provided'}"],
        )
        self._grants[grant.id] = grant
        return grant

    def evaluate_request(self, request: ExposureRequest, item: InventoryItem | None = None) -> ExposureEvaluation:
        resource = item or self.inventory.get(request.resource_id)
        if not resource.enabled:
            return ExposureEvaluation(ExposureDecision.DENY, "resource is disabled")
        if resource.access == AccessMode.DENIED:
            return ExposureEvaluation(ExposureDecision.DENY, "resource access is denied")
        if request.ttl_seconds <= 0:
            return ExposureEvaluation(ExposureDecision.DENY, "ttl must be positive")
        if request.ttl_seconds > 24 * 3600:
            return ExposureEvaluation(ExposureDecision.DENY, "ttl exceeds 24h MVP safety limit")
        if request.requested_exposure == ExposureMode.PUBLIC:
            if resource.exposure != ExposureMode.PUBLIC:
                return ExposureEvaluation(ExposureDecision.DENY, "resource is not marked public")
            if resource.sensitivity != Sensitivity.PUBLIC:
                return ExposureEvaluation(ExposureDecision.DENY, "only public sensitivity resources can be public")
        if resource.exposure == ExposureMode.PRIVATE and request.requested_exposure != ExposureMode.AUTHENTICATED:
            return ExposureEvaluation(ExposureDecision.DENY, "private resources require authenticated gateway exposure")
        for permission in request.permissions:
            if not resource.supports_permission(permission):
                return ExposureEvaluation(ExposureDecision.DENY, f"unsupported permission: {permission}")
        if request.allow_download and resource.kind in {"camera", "microphone", "sensor"}:
            return ExposureEvaluation(ExposureDecision.DENY, "raw device downloads are not allowed by default")
        return ExposureEvaluation(ExposureDecision.ALLOW, "request allowed")

    def can_access(self, grant_id: str, *, subject: str, permission: str, now: datetime | None = None) -> ExposureEvaluation:
        grant = self._grants.get(grant_id)
        if not grant:
            return ExposureEvaluation(ExposureDecision.DENY, "unknown grant")
        if not grant.is_active(now=now):
            return ExposureEvaluation(ExposureDecision.DENY, "grant is expired or revoked", grant)
        if grant.subject != subject:
            return ExposureEvaluation(ExposureDecision.DENY, "subject mismatch", grant)
        if permission not in grant.permissions:
            return ExposureEvaluation(ExposureDecision.DENY, "permission not in grant", grant)
        grant.audit.append(f"access:{subject}:{permission}")
        return ExposureEvaluation(ExposureDecision.ALLOW, "grant active", grant)

    def revoke(self, grant_id: str, *, reason: str = "") -> None:
        grant = self._grants.get(grant_id)
        if grant:
            grant.revoked = True
            grant.audit.append(f"revoked:{reason or 'no reason provided'}")

    def cleanup_expired(self, *, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        expired = [grant_id for grant_id, grant in self._grants.items() if not grant.is_active(now=current)]
        for grant_id in expired:
            del self._grants[grant_id]
        return len(expired)
