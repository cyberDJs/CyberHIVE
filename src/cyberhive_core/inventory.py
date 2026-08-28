"""CyberHIVE Inventory MVP.

Inventory is the canonical registry of resources CyberHIVE knows about. It
separates four concerns that are often mixed together:

- enabled/disabled: whether the resource exists in active operation
- indexing: whether its content may be indexed for Knowledge retrieval
- access: whether agents/users may use it directly, behind a gate, or never
- exposure: whether it is private, LAN-only, authenticated, or public-facing
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IndexingMode(str, Enum):
    INDEXED = "indexed"
    NON_INDEXED = "non_indexed"


class AccessMode(str, Enum):
    ALLOWED = "allowed"
    GATED = "gated"
    DENIED = "denied"


class ExposureMode(str, Enum):
    PRIVATE = "private"
    LAN = "lan"
    AUTHENTICATED = "authenticated"
    PUBLIC = "public"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    SECRET = "secret"


@dataclass(frozen=True)
class Capability:
    """A named resource capability.

    Examples:
    - video.stream
    - video.snapshot
    - model.infer
    - file.read
    - sensor.observe
    """

    name: str
    permissions: tuple[str, ...] = ()

    def supports(self, permission: str) -> bool:
        return permission in self.permissions or not self.permissions


@dataclass
class InventoryItem:
    id: str
    kind: str
    name: str
    enabled: bool = True
    indexing: IndexingMode = IndexingMode.NON_INDEXED
    access: AccessMode = AccessMode.GATED
    exposure: ExposureMode = ExposureMode.PRIVATE
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    capabilities: list[Capability] = field(default_factory=list)
    owner: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_capability(self, capability_name: str) -> bool:
        return any(cap.name == capability_name for cap in self.capabilities)

    def supports_permission(self, permission: str) -> bool:
        return any(cap.supports(permission) for cap in self.capabilities)

    def is_indexable(self) -> bool:
        return self.enabled and self.indexing == IndexingMode.INDEXED

    def is_usable(self) -> bool:
        return self.enabled and self.access != AccessMode.DENIED

    def validate(self) -> None:
        if not self.id:
            raise ValueError("inventory item id is required")
        if not self.kind:
            raise ValueError("inventory item kind is required")
        if self.exposure == ExposureMode.PUBLIC and self.sensitivity in {Sensitivity.SENSITIVE, Sensitivity.SECRET}:
            raise ValueError("sensitive or secret resources cannot be public")
        if self.exposure == ExposureMode.PUBLIC and self.access == AccessMode.DENIED:
            raise ValueError("public exposure with denied access is inconsistent")
        if self.indexing == IndexingMode.INDEXED and self.sensitivity == Sensitivity.SECRET:
            raise ValueError("secret resources cannot be indexed")


class InventoryRegistry:
    """In-memory registry for the MVP.

    This can later be backed by PostgreSQL or an embedded local store without
    changing the public model.
    """

    def __init__(self) -> None:
        self._items: dict[str, InventoryItem] = {}

    def add(self, item: InventoryItem) -> None:
        item.validate()
        if item.id in self._items:
            raise ValueError(f"inventory item already exists: {item.id}")
        self._items[item.id] = item

    def upsert(self, item: InventoryItem) -> None:
        item.validate()
        self._items[item.id] = item

    def get(self, item_id: str) -> InventoryItem:
        try:
            return self._items[item_id]
        except KeyError as exc:
            raise KeyError(f"unknown inventory item: {item_id}") from exc

    def list(self, *, enabled: bool | None = None, kind: str | None = None) -> list[InventoryItem]:
        values = list(self._items.values())
        if enabled is not None:
            values = [item for item in values if item.enabled is enabled]
        if kind is not None:
            values = [item for item in values if item.kind == kind]
        return sorted(values, key=lambda item: item.id)

    def by_capability(self, capability_name: str) -> list[InventoryItem]:
        return [item for item in self.list(enabled=True) if item.has_capability(capability_name)]

    def set_enabled(self, item_id: str, enabled: bool) -> None:
        item = self.get(item_id)
        item.enabled = enabled
        item.validate()

    def validate_all(self) -> None:
        for item in self._items.values():
            item.validate()
