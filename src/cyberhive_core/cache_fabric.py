"""Cache & Reuse Fabric MVP."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CachePolicy:
    """Security and freshness policy for one cache write."""

    ttl_seconds: int | None = None
    freshness: str = "bounded_stale"
    sensitivity: str = "internal"
    allow_secret: bool = False


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at_ns: int
    policy: CachePolicy
    hit_count: int = 0
    dependency_versions: dict[str, str] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.policy.ttl_seconds is None:
            return False
        age_seconds = (time.time_ns() - self.created_at_ns) / 1_000_000_000
        return age_seconds > self.policy.ttl_seconds


class CacheFabric:
    """Small in-memory cache with deterministic composite cache keys."""

    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}

    @staticmethod
    def make_key(
        *,
        operation: str,
        normalized_input: Any,
        relevant_state: Any = None,
        model_version: str | None = None,
        configuration: Any = None,
        permissions_hash: str | None = None,
        dependency_versions: dict[str, str] | None = None,
    ) -> str:
        material = {
            "operation": operation,
            "normalized_input": normalized_input,
            "relevant_state": relevant_state,
            "model_version": model_version,
            "configuration": configuration,
            "permissions_hash": permissions_hash,
            "dependency_versions": dependency_versions or {},
        }
        raw = json.dumps(material, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def put(
        self,
        key: str,
        value: Any,
        *,
        policy: CachePolicy | None = None,
        dependency_versions: dict[str, str] | None = None,
    ) -> None:
        policy = policy or CachePolicy()
        if policy.sensitivity == "secret" and not policy.allow_secret:
            raise ValueError("Refusing to cache secret data without allow_secret=True")
        self._entries[key] = CacheEntry(
            key=key,
            value=value,
            created_at_ns=time.time_ns(),
            policy=policy,
            dependency_versions=dependency_versions or {},
        )

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            self._entries.pop(key, None)
            return None
        entry.hit_count += 1
        return entry.value

    def stats(self) -> dict[str, Any]:
        return {
            "entries": len(self._entries),
            "hits": sum(entry.hit_count for entry in self._entries.values()),
        }
