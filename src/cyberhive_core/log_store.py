"""Append-only JSONL log store for HiveFrames."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from .hiveframe import HiveFrame


class AppendOnlyLog:
    """Durable append-only frame log.

    This is deliberately small and boring. It gives the Runtime Bus a durable
    local trail before the project chooses a heavier event-log backend.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append_frame(self, frame: HiveFrame) -> None:
        with self.path.open("ab") as handle:
            handle.write(frame.encode_json())
            handle.write(b"\n")

    def iter_frames(self) -> Iterator[HiveFrame]:
        with self.path.open("rb") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield HiveFrame.decode_json(line)

    def count(self) -> int:
        with self.path.open("rb") as handle:
            return sum(1 for line in handle if line.strip())

    def truncate(self) -> None:
        self.path.write_bytes(b"")
