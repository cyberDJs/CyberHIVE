"""HiveFrame transport primitives.

The proto definition in ``proto/hiveframe.proto`` remains the future wire
contract. This module provides a pure-stdlib JSON-lines implementation for the
MVP so the repository can run immediately without a protobuf toolchain.
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


class OperationType(str, Enum):
    """Operation types used by the internal Runtime Bus."""

    SET = "set"
    PATCH = "patch"
    DELETE = "delete"
    OBSERVE = "observe"
    COMMAND = "command"
    RESULT = "result"
    ACK = "ack"
    ERROR = "error"


@dataclass(slots=True)
class Operation:
    """One operation inside a HiveFrame."""

    type: OperationType
    resource_id: str
    payload: bytes = b""
    content_type: str = "application/json"
    deadline_ns: int = 0
    priority: int = 0

    @classmethod
    def from_json_payload(
        cls,
        operation_type: OperationType | str,
        resource_id: str,
        payload: Any,
        *,
        priority: int = 0,
        deadline_ns: int = 0,
    ) -> "Operation":
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return cls(
            type=OperationType(operation_type),
            resource_id=resource_id,
            payload=raw,
            content_type="application/json",
            priority=priority,
            deadline_ns=deadline_ns,
        )

    def json_payload(self) -> Any:
        if not self.payload:
            return None
        return json.loads(self.payload.decode("utf-8"))

    def encoded_size(self) -> int:
        return len(self.payload) + len(self.resource_id.encode("utf-8")) + 64

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "resource_id": self.resource_id,
            "content_type": self.content_type,
            "payload_b64": base64.b64encode(self.payload).decode("ascii"),
            "deadline_ns": self.deadline_ns,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Operation":
        return cls(
            type=OperationType(data["type"]),
            resource_id=str(data["resource_id"]),
            content_type=str(data.get("content_type", "application/json")),
            payload=base64.b64decode(data.get("payload_b64", "")),
            deadline_ns=int(data.get("deadline_ns", 0)),
            priority=int(data.get("priority", 0)),
        )


@dataclass(slots=True)
class HiveFrame:
    """Batch frame for internal CyberHIVE runtime transport."""

    version: int
    node_id: str
    sequence: int
    timestamp_ns: int
    base_state_revision: int
    operations: list[Operation] = field(default_factory=list)
    compression: str = "none"

    CURRENT_VERSION: ClassVar[int] = 1

    @classmethod
    def new(
        cls,
        *,
        node_id: str,
        sequence: int,
        base_state_revision: int,
        operations: list[Operation],
    ) -> "HiveFrame":
        return cls(
            version=cls.CURRENT_VERSION,
            node_id=node_id,
            sequence=sequence,
            timestamp_ns=time.time_ns(),
            base_state_revision=base_state_revision,
            operations=list(operations),
        )

    def encoded_size(self) -> int:
        return sum(op.encoded_size() for op in self.operations) + 128

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "node_id": self.node_id,
            "sequence": self.sequence,
            "timestamp_ns": self.timestamp_ns,
            "base_state_revision": self.base_state_revision,
            "compression": self.compression,
            "operations": [operation.to_dict() for operation in self.operations],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HiveFrame":
        return cls(
            version=int(data["version"]),
            node_id=str(data["node_id"]),
            sequence=int(data["sequence"]),
            timestamp_ns=int(data["timestamp_ns"]),
            base_state_revision=int(data.get("base_state_revision", 0)),
            compression=str(data.get("compression", "none")),
            operations=[Operation.from_dict(item) for item in data.get("operations", [])],
        )

    def encode_json(self) -> bytes:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    @classmethod
    def decode_json(cls, raw: bytes | str) -> "HiveFrame":
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return cls.from_dict(json.loads(raw))
