"""CyberHIVE Cache & Reuse Fabric MVP.

This module adds a deterministic reuse layer above the runtime bus, knowledge
retrieval, data fabric and agent planning layers.

The MVP intentionally avoids distributed cache infrastructure. It provides the
core semantics first:

* canonical cache keys,
* TTL and revision-aware entries,
* sensitivity-aware cache policy,
* exact result cache,
* semantic intent cache,
* state cache,
* artifact metadata cache,
* plan cache / execution pattern memory,
* a small cost model that answers: reuse or recompute?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Iterable, Mapping


class CacheScope(str, Enum):
    PUBLIC = "public"
    TENANT = "tenant"
    USER = "user"
    SESSION = "session"
    PRIVATE = "private"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    SECRET = "secret"


class CacheKind(str, Enum):
    EXACT_RESULT = "exact_result"
    SEMANTIC = "semantic"
    STATE = "state"
    ARTIFACT = "artifact"
    PLAN = "plan"
    MATERIALIZED_VIEW = "materialized_view"


class ReuseAction(str, Enum):
    REUSE_EXACT = "reuse_exact"
    REUSE_SEMANTIC = "reuse_semantic"
    REUSE_STATE = "reuse_state"
    REUSE_ARTIFACT = "reuse_artifact"
    REUSE_PLAN = "reuse_plan"
    RECOMPUTE = "recompute"
    DENY_CACHE = "deny_cache"


@dataclass(frozen=True)
class CachePolicy:
    """Rules controlling whether an object may be cached."""

    allow_secret_cache: bool = False
    max_ttl_seconds_public: int = 3600
    max_ttl_seconds_internal: int = 900
    max_ttl_seconds_sensitive: int = 300
    max_ttl_seconds_secret: int = 30
    require_acl_for_sensitive: bool = True

    def ttl_for(self, sensitivity: Sensitivity, requested_ttl_seconds: int | None) -> int:
        if sensitivity == Sensitivity.PUBLIC:
            cap = self.max_ttl_seconds_public
        elif sensitivity == Sensitivity.INTERNAL:
            cap = self.max_ttl_seconds_internal
        elif sensitivity == Sensitivity.SENSITIVE:
            cap = self.max_ttl_seconds_sensitive
        else:
            cap = self.max_ttl_seconds_secret
        if requested_ttl_seconds is None:
            return cap
        return max(0, min(cap, int(requested_ttl_seconds)))

    def cache_allowed(
        self,
        *,
        sensitivity: Sensitivity,
        scope: CacheScope,
        acl: tuple[str, ...],
        persist_to_disk: bool,
    ) -> tuple[bool, str]:
        if sensitivity == Sensitivity.SECRET and not self.allow_secret_cache:
            return False, "secret data is not cacheable by default"
        if sensitivity in {Sensitivity.SENSITIVE, Sensitivity.SECRET} and scope in {CacheScope.PUBLIC, CacheScope.TENANT}:
            return False, "sensitive data requires user/session/private scope"
        if self.require_acl_for_sensitive and sensitivity in {Sensitivity.SENSITIVE, Sensitivity.SECRET} and not acl:
            return False, "sensitive cache entries require an ACL"
        if sensitivity == Sensitivity.SECRET and persist_to_disk:
            return False, "secret data cannot be persisted to disk in the MVP"
        return True, "allowed"


@dataclass(frozen=True)
class CanonicalOperation:
    """A normalized operation signature used as a stable cache key input."""

    operation: str
    normalized_input: Mapping[str, Any] = field(default_factory=dict)
    relevant_state: Mapping[str, Any] = field(default_factory=dict)
    model_version: str | None = None
    configuration: Mapping[str, Any] = field(default_factory=dict)
    permissions: tuple[str, ...] = ()
    dependency_versions: Mapping[str, str] = field(default_factory=dict)
    revision: str | int | None = None

    def fingerprint_payload(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "normalized_input": _stable(self.normalized_input),
            "relevant_state": _stable(self.relevant_state),
            "model_version": self.model_version,
            "configuration": _stable(self.configuration),
            "permissions": sorted(self.permissions),
            "dependency_versions": _stable(self.dependency_versions),
            "revision": self.revision,
        }

    def key(self) -> str:
        return stable_hash(self.fingerprint_payload())


@dataclass
class CacheEntry:
    key: str
    kind: CacheKind
    value: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 300
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    scope: CacheScope = CacheScope.SESSION
    acl: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    revision: str | int | None = None
    dependencies: tuple[str, ...] = ()
    hits: int = 0
    last_hit_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def expires_at(self) -> datetime:
        return self.created_at + timedelta(seconds=self.ttl_seconds)

    def expired(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        return current >= self.expires_at

    def allowed_for(self, subject: str | None) -> bool:
        if not self.acl:
            return True
        return subject in self.acl

    def touch(self) -> None:
        self.hits += 1
        self.last_hit_at = datetime.now(timezone.utc)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "kind": self.kind.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "sensitivity": self.sensitivity.value,
            "scope": self.scope.value,
            "tags": list(self.tags),
            "revision": self.revision,
            "dependencies": list(self.dependencies),
            "hits": self.hits,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SemanticIntent:
    intent: str
    entities: Mapping[str, str] = field(default_factory=dict)
    qualifiers: Mapping[str, Any] = field(default_factory=dict)
    revision: str | int | None = None

    def key(self) -> str:
        return stable_hash(
            {
                "intent": self.intent,
                "entities": _stable(self.entities),
                "qualifiers": _stable(self.qualifiers),
                "revision": self.revision,
            }
        )


@dataclass(frozen=True)
class ExecutionCost:
    cpu_ms: float = 0.0
    gpu_ms: float = 0.0
    io_bytes: int = 0
    network_bytes: int = 0
    wall_ms: float = 0.0
    token_count: int = 0
    tool_calls: int = 0

    def score(self) -> float:
        """Resource cost score, not a monetary price."""

        return (
            self.cpu_ms / 1000.0
            + self.gpu_ms / 750.0
            + self.wall_ms / 500.0
            + self.io_bytes / 25_000_000
            + self.network_bytes / 10_000_000
            + self.token_count / 8000.0
            + self.tool_calls * 0.2
        )


@dataclass(frozen=True)
class ReuseDecision:
    action: ReuseAction
    cache_key: str | None = None
    reason: str = ""
    confidence: float = 0.0
    estimated_saved_score: float = 0.0
    entry: CacheEntry | None = None
    pattern_id: str | None = None


@dataclass
class ExecutionPattern:
    """A reusable plan shape learned from repeated workflow executions."""

    id: str
    pattern_type: str
    signature: Mapping[str, Any]
    preferred_plan: tuple[str, ...]
    observed_cost: ExecutionCost = field(default_factory=ExecutionCost)
    success_rate: float = 1.0
    uses: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def key(self) -> str:
        return stable_hash({"pattern_type": self.pattern_type, "signature": _stable(self.signature)})

    def record_use(self, success: bool = True) -> None:
        old_uses = self.uses
        self.uses += 1
        # Running average of success rate.
        self.success_rate = ((self.success_rate * old_uses) + (1.0 if success else 0.0)) / max(1, self.uses)
        self.updated_at = datetime.now(timezone.utc)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "signature": _stable(self.signature),
            "preferred_plan": list(self.preferred_plan),
            "observed_cost": {
                "cpu_ms": self.observed_cost.cpu_ms,
                "gpu_ms": self.observed_cost.gpu_ms,
                "io_bytes": self.observed_cost.io_bytes,
                "network_bytes": self.observed_cost.network_bytes,
                "wall_ms": self.observed_cost.wall_ms,
                "token_count": self.observed_cost.token_count,
                "tool_calls": self.observed_cost.tool_calls,
            },
            "success_rate": self.success_rate,
            "uses": self.uses,
            "updated_at": self.updated_at.isoformat(),
            "metadata": dict(self.metadata),
        }


class InMemoryCacheStore:
    """Small in-process cache store for the MVP."""

    def __init__(self) -> None:
        self.entries: dict[str, CacheEntry] = {}
        self.semantic_to_exact: dict[str, str] = {}
        self.state_entries: dict[str, str] = {}
        self.artifact_entries: dict[str, str] = {}
        self.patterns: dict[str, ExecutionPattern] = {}

    def put(self, entry: CacheEntry) -> CacheEntry:
        self.entries[entry.key] = entry
        return entry

    def get(self, key: str, *, subject: str | None = None, now: datetime | None = None) -> CacheEntry | None:
        entry = self.entries.get(key)
        if not entry:
            return None
        if entry.expired(now):
            self.entries.pop(key, None)
            return None
        if not entry.allowed_for(subject):
            return None
        entry.touch()
        return entry

    def invalidate_key(self, key: str) -> bool:
        existed = key in self.entries
        self.entries.pop(key, None)
        for mapping in (self.semantic_to_exact, self.state_entries, self.artifact_entries):
            for alias, target in list(mapping.items()):
                if target == key:
                    mapping.pop(alias, None)
        return existed

    def invalidate_by_dependency(self, dependency: str) -> int:
        removed = 0
        for key, entry in list(self.entries.items()):
            if dependency in entry.dependencies:
                self.invalidate_key(key)
                removed += 1
        return removed

    def cleanup_expired(self, now: datetime | None = None) -> int:
        removed = 0
        for key, entry in list(self.entries.items()):
            if entry.expired(now):
                self.invalidate_key(key)
                removed += 1
        return removed

    def put_pattern(self, pattern: ExecutionPattern) -> ExecutionPattern:
        self.patterns[pattern.key()] = pattern
        return pattern

    def get_pattern(self, pattern_type: str, signature: Mapping[str, Any]) -> ExecutionPattern | None:
        return self.patterns.get(stable_hash({"pattern_type": pattern_type, "signature": _stable(signature)}))


class CostModel:
    """Decides whether reuse is cheaper than recomputation in resource terms."""

    def should_reuse(
        self,
        *,
        recompute_cost: ExecutionCost,
        lookup_cost: ExecutionCost | None = None,
        freshness_tolerance_seconds: int = 0,
        entry_age_seconds: float = 0.0,
        confidence: float = 1.0,
    ) -> tuple[bool, float, str]:
        lookup = lookup_cost or ExecutionCost(wall_ms=5, cpu_ms=2)
        saved = max(0.0, recompute_cost.score() - lookup.score())
        if freshness_tolerance_seconds > 0 and entry_age_seconds > freshness_tolerance_seconds:
            return False, saved, "entry is older than freshness tolerance"
        if confidence < 0.75:
            return False, saved, "confidence below reuse threshold"
        if saved <= 0.01:
            return False, saved, "recompute is cheap enough"
        return True, saved, "reuse is cheaper than recompute"


class CacheFabric:
    """Unified exact, semantic, state, artifact and plan cache facade."""

    def __init__(self, store: InMemoryCacheStore | None = None, policy: CachePolicy | None = None) -> None:
        self.store = store or InMemoryCacheStore()
        self.policy = policy or CachePolicy()
        self.cost_model = CostModel()

    def put_exact(
        self,
        operation: CanonicalOperation,
        value: Any,
        *,
        sensitivity: Sensitivity = Sensitivity.INTERNAL,
        scope: CacheScope = CacheScope.SESSION,
        ttl_seconds: int | None = None,
        acl: Iterable[str] = (),
        dependencies: Iterable[str] = (),
        tags: Iterable[str] = (),
        persist_to_disk: bool = False,
    ) -> CacheEntry:
        return self._put(
            key=operation.key(),
            kind=CacheKind.EXACT_RESULT,
            value=value,
            sensitivity=sensitivity,
            scope=scope,
            ttl_seconds=ttl_seconds,
            acl=tuple(acl),
            dependencies=tuple(dependencies),
            tags=tuple(tags),
            revision=operation.revision,
            persist_to_disk=persist_to_disk,
        )

    def get_exact(self, operation: CanonicalOperation, *, subject: str | None = None) -> CacheEntry | None:
        return self.store.get(operation.key(), subject=subject)

    def put_semantic(
        self,
        intent: SemanticIntent,
        value: Any,
        *,
        sensitivity: Sensitivity = Sensitivity.INTERNAL,
        scope: CacheScope = CacheScope.SESSION,
        ttl_seconds: int | None = None,
        acl: Iterable[str] = (),
        dependencies: Iterable[str] = (),
        tags: Iterable[str] = (),
    ) -> CacheEntry:
        entry = self._put(
            key=f"sem:{intent.key()}",
            kind=CacheKind.SEMANTIC,
            value=value,
            sensitivity=sensitivity,
            scope=scope,
            ttl_seconds=ttl_seconds,
            acl=tuple(acl),
            dependencies=tuple(dependencies),
            tags=tuple(tags),
            revision=intent.revision,
            persist_to_disk=False,
        )
        self.store.semantic_to_exact[intent.key()] = entry.key
        return entry

    def get_semantic(self, intent: SemanticIntent, *, subject: str | None = None) -> CacheEntry | None:
        key = self.store.semantic_to_exact.get(intent.key(), f"sem:{intent.key()}")
        return self.store.get(key, subject=subject)

    def put_state(
        self,
        state_id: str,
        revision: str | int,
        value: Any,
        *,
        ttl_seconds: int | None = 60,
        dependencies: Iterable[str] = (),
    ) -> CacheEntry:
        key = stable_hash({"state_id": state_id, "revision": revision})
        entry = self._put(
            key=f"state:{key}",
            kind=CacheKind.STATE,
            value=value,
            sensitivity=Sensitivity.INTERNAL,
            scope=CacheScope.TENANT,
            ttl_seconds=ttl_seconds,
            acl=(),
            dependencies=tuple(dependencies),
            tags=("state", state_id),
            revision=revision,
            persist_to_disk=False,
        )
        self.store.state_entries[state_id] = entry.key
        return entry

    def get_state(self, state_id: str) -> CacheEntry | None:
        key = self.store.state_entries.get(state_id)
        if not key:
            return None
        return self.store.get(key)

    def put_artifact(
        self,
        artifact_id: str,
        metadata: Mapping[str, Any],
        *,
        content_hash: str,
        sensitivity: Sensitivity = Sensitivity.INTERNAL,
        ttl_seconds: int | None = None,
        dependencies: Iterable[str] = (),
    ) -> CacheEntry:
        key = stable_hash({"artifact_id": artifact_id, "content_hash": content_hash})
        entry = self._put(
            key=f"artifact:{key}",
            kind=CacheKind.ARTIFACT,
            value=dict(metadata),
            sensitivity=sensitivity,
            scope=CacheScope.TENANT if sensitivity in {Sensitivity.PUBLIC, Sensitivity.INTERNAL} else CacheScope.PRIVATE,
            ttl_seconds=ttl_seconds,
            acl=(),
            dependencies=tuple(dependencies),
            tags=("artifact", artifact_id),
            revision=content_hash,
            persist_to_disk=False,
        )
        self.store.artifact_entries[artifact_id] = entry.key
        return entry

    def get_artifact(self, artifact_id: str) -> CacheEntry | None:
        key = self.store.artifact_entries.get(artifact_id)
        if not key:
            return None
        return self.store.get(key)

    def record_pattern(self, pattern: ExecutionPattern) -> ExecutionPattern:
        return self.store.put_pattern(pattern)

    def get_pattern(self, pattern_type: str, signature: Mapping[str, Any]) -> ExecutionPattern | None:
        return self.store.get_pattern(pattern_type, signature)

    def choose_reuse(
        self,
        operation: CanonicalOperation,
        *,
        recompute_cost: ExecutionCost,
        subject: str | None = None,
        freshness_tolerance_seconds: int = 0,
    ) -> ReuseDecision:
        entry = self.get_exact(operation, subject=subject)
        if not entry:
            return ReuseDecision(action=ReuseAction.RECOMPUTE, reason="no exact cache entry", confidence=0.0)
        age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
        reuse, saved, reason = self.cost_model.should_reuse(
            recompute_cost=recompute_cost,
            freshness_tolerance_seconds=freshness_tolerance_seconds,
            entry_age_seconds=age,
            confidence=1.0,
        )
        if not reuse:
            return ReuseDecision(
                action=ReuseAction.RECOMPUTE,
                cache_key=entry.key,
                reason=reason,
                confidence=1.0,
                estimated_saved_score=saved,
                entry=entry,
            )
        return ReuseDecision(
            action=ReuseAction.REUSE_EXACT,
            cache_key=entry.key,
            reason=reason,
            confidence=1.0,
            estimated_saved_score=saved,
            entry=entry,
        )

    def _put(
        self,
        *,
        key: str,
        kind: CacheKind,
        value: Any,
        sensitivity: Sensitivity,
        scope: CacheScope,
        ttl_seconds: int | None,
        acl: tuple[str, ...],
        dependencies: tuple[str, ...],
        tags: tuple[str, ...],
        revision: str | int | None,
        persist_to_disk: bool,
    ) -> CacheEntry:
        allowed, reason = self.policy.cache_allowed(
            sensitivity=sensitivity,
            scope=scope,
            acl=acl,
            persist_to_disk=persist_to_disk,
        )
        if not allowed:
            raise ValueError(f"cache denied: {reason}")
        ttl = self.policy.ttl_for(sensitivity, ttl_seconds)
        entry = CacheEntry(
            key=key,
            kind=kind,
            value=value,
            ttl_seconds=ttl,
            sensitivity=sensitivity,
            scope=scope,
            acl=acl,
            dependencies=dependencies,
            tags=tags,
            revision=revision,
        )
        return self.store.put(entry)


class ReuseEngine:
    """Higher-level facade for workflow reuse decisions."""

    def __init__(self, cache: CacheFabric | None = None) -> None:
        self.cache = cache or CacheFabric()

    def resolve_operation(
        self,
        operation: CanonicalOperation,
        *,
        recompute_cost: ExecutionCost,
        subject: str | None = None,
        freshness_tolerance_seconds: int = 0,
    ) -> ReuseDecision:
        return self.cache.choose_reuse(
            operation,
            recompute_cost=recompute_cost,
            subject=subject,
            freshness_tolerance_seconds=freshness_tolerance_seconds,
        )

    def resolve_pattern(
        self,
        pattern_type: str,
        signature: Mapping[str, Any],
        *,
        min_success_rate: float = 0.9,
    ) -> ReuseDecision:
        pattern = self.cache.get_pattern(pattern_type, signature)
        if not pattern:
            return ReuseDecision(action=ReuseAction.RECOMPUTE, reason="no reusable execution pattern")
        if pattern.success_rate < min_success_rate:
            return ReuseDecision(
                action=ReuseAction.RECOMPUTE,
                pattern_id=pattern.id,
                reason="pattern success rate below threshold",
                confidence=pattern.success_rate,
            )
        confidence = min(1.0, pattern.success_rate * (1.0 - math.exp(-max(1, pattern.uses) / 5)))
        return ReuseDecision(
            action=ReuseAction.REUSE_PLAN,
            pattern_id=pattern.id,
            reason="reusable execution pattern found",
            confidence=round(confidence, 4),
            estimated_saved_score=pattern.observed_cost.score(),
        )


def stable_hash(value: Any) -> str:
    payload = json.dumps(_stable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _stable(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_stable(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value
