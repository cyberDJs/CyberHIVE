"""Runtime Bus and micro-batching primitives."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from .hiveframe import HiveFrame, Operation
from .log_store import AppendOnlyLog
from .state_engine import StateEngine

FrameHandler = Callable[[HiveFrame], None]


@dataclass
class MicroBatcher:
    """Collects operations and flushes them as a batch.

    Flush conditions:
    - max operation count reached
    - max approximate byte size reached
    - max latency window reached
    - high-priority operation arrives
    """

    flush_callback: Callable[[list[Operation]], None]
    max_ops: int = 128
    max_bytes: int = 64 * 1024
    max_latency_ms: float = 5.0
    high_priority_threshold: int = 100
    _buffer: list[Operation] = field(default_factory=list, init=False)
    _buffer_bytes: int = field(default=0, init=False)
    _opened_at_ns: int = field(default=0, init=False)

    def add(self, operation: Operation) -> None:
        now_ns = time.monotonic_ns()
        if not self._buffer:
            self._opened_at_ns = now_ns
        self._buffer.append(operation)
        self._buffer_bytes += operation.encoded_size()
        if self.should_flush(now_ns=now_ns, latest_operation=operation):
            self.flush()

    def should_flush(self, *, now_ns: int | None = None, latest_operation: Operation | None = None) -> bool:
        if not self._buffer:
            return False
        if latest_operation and latest_operation.priority >= self.high_priority_threshold:
            return True
        if len(self._buffer) >= self.max_ops:
            return True
        if self._buffer_bytes >= self.max_bytes:
            return True
        now_ns = now_ns if now_ns is not None else time.monotonic_ns()
        elapsed_ms = (now_ns - self._opened_at_ns) / 1_000_000
        return elapsed_ms >= self.max_latency_ms

    def flush(self) -> None:
        if not self._buffer:
            return
        operations = self._buffer
        self._buffer = []
        self._buffer_bytes = 0
        self._opened_at_ns = 0
        self.flush_callback(operations)

    @property
    def pending_count(self) -> int:
        return len(self._buffer)


@dataclass
class RuntimeBus:
    """Local MVP Runtime Bus.

    Each flush creates a HiveFrame, appends it to the durable log, applies it to
    StateEngine and then notifies subscribers.
    """

    node_id: str
    log_store: AppendOnlyLog
    state_engine: StateEngine
    max_ops: int = 128
    max_bytes: int = 64 * 1024
    max_latency_ms: float = 5.0
    sequence: int = 0
    subscribers: list[FrameHandler] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.batcher = MicroBatcher(
            flush_callback=self._flush_operations,
            max_ops=self.max_ops,
            max_bytes=self.max_bytes,
            max_latency_ms=self.max_latency_ms,
        )

    def publish(self, operation: Operation) -> None:
        self.batcher.add(operation)

    def flush(self) -> None:
        self.batcher.flush()

    def subscribe(self, handler: FrameHandler) -> None:
        self.subscribers.append(handler)

    def _flush_operations(self, operations: list[Operation]) -> None:
        self.sequence += 1
        frame = HiveFrame.new(
            node_id=self.node_id,
            sequence=self.sequence,
            base_state_revision=self.state_engine.revision,
            operations=operations,
        )
        self.log_store.append_frame(frame)
        self.state_engine.apply_frame(frame)
        for subscriber in self.subscribers:
            subscriber(frame)
