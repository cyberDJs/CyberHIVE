"""Runtime state engine with revisioned SET/PATCH/DELETE/OBSERVE support."""
from __future__ import annotations

import copy
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .hiveframe import HiveFrame, Operation, OperationType


def _split_path(resource_id: str) -> list[str]:
    return [part for part in resource_id.replace("/", ".").split(".") if part]


def _deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value
    return target


@dataclass
class StateEngine:
    """Maintains current runtime state and applies HiveFrame deltas."""

    max_recent_observations: int = 1000
    revision: int = 0
    state: dict[str, Any] = field(default_factory=dict)
    recent_observations: deque[dict[str, Any]] = field(default_factory=deque)

    def __post_init__(self) -> None:
        self.recent_observations = deque(maxlen=self.max_recent_observations)

    def snapshot(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "state": copy.deepcopy(self.state),
            "recent_observations": list(self.recent_observations),
        }

    def apply_frame(self, frame: HiveFrame) -> int:
        for operation in frame.operations:
            self.apply_operation(operation)
        return self.revision

    def apply_operation(self, operation: Operation) -> int:
        if operation.type == OperationType.SET:
            self._set(operation.resource_id, operation.json_payload())
        elif operation.type == OperationType.PATCH:
            self._patch(operation.resource_id, operation.json_payload())
        elif operation.type == OperationType.DELETE:
            self._delete(operation.resource_id)
        elif operation.type == OperationType.OBSERVE:
            payload = operation.json_payload()
            if not isinstance(payload, dict):
                payload = {"value": payload}
            self.recent_observations.append(
                {
                    "resource_id": operation.resource_id,
                    "payload": payload,
                    "priority": operation.priority,
                }
            )
        self.revision += 1
        return self.revision

    def _navigate(self, resource_id: str, create: bool = False) -> tuple[dict[str, Any], str]:
        parts = _split_path(resource_id)
        if not parts:
            raise ValueError("resource_id must not be empty")
        current = self.state
        for part in parts[:-1]:
            if part not in current:
                if not create:
                    return {}, parts[-1]
                current[part] = {}
            if not isinstance(current[part], dict):
                if not create:
                    return {}, parts[-1]
                current[part] = {}
            current = current[part]
        return current, parts[-1]

    def _set(self, resource_id: str, value: Any) -> None:
        parent, key = self._navigate(resource_id, create=True)
        parent[key] = value

    def _patch(self, resource_id: str, value: Any) -> None:
        if not isinstance(value, dict):
            self._set(resource_id, value)
            return
        parent, key = self._navigate(resource_id, create=True)
        if not isinstance(parent.get(key), dict):
            parent[key] = {}
        _deep_merge(parent[key], value)

    def _delete(self, resource_id: str) -> None:
        parent, key = self._navigate(resource_id, create=False)
        if parent:
            parent.pop(key, None)
