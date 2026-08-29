#!/usr/bin/env python3
"""Validate CyberHIVE Inventory + Exposure Gateway MVP."""
from __future__ import annotations

from cyberhive_core import (
    AccessMode,
    Capability,
    ExposureDecision,
    ExposureGateway,
    ExposureMode,
    ExposureRequest,
    IndexingMode,
    InventoryItem,
    InventoryRegistry,
    Sensitivity,
)


def main() -> int:
    registry = InventoryRegistry()
    registry.add(
        InventoryItem(
            id="camera.garden",
            kind="camera",
            name="Garden Camera",
            enabled=True,
            indexing=IndexingMode.NON_INDEXED,
            access=AccessMode.GATED,
            exposure=ExposureMode.PRIVATE,
            sensitivity=Sensitivity.SENSITIVE,
            capabilities=[Capability("video.stream", ("stream.read",)), Capability("video.snapshot", ("snapshot.read",))],
        )
    )
    registry.add(
        InventoryItem(
            id="docs.project_context",
            kind="document",
            name="Project Context",
            enabled=True,
            indexing=IndexingMode.INDEXED,
            access=AccessMode.ALLOWED,
            exposure=ExposureMode.PUBLIC,
            sensitivity=Sensitivity.PUBLIC,
            capabilities=[Capability("document.read", ("read",))],
        )
    )
    registry.validate_all()

    gateway = ExposureGateway(registry)
    grant = gateway.create_grant(
        ExposureRequest(
            resource_id="camera.garden",
            subject="demo-user",
            permissions=("stream.read",),
            ttl_seconds=300,
            reason="MVP smoke test",
        )
    )
    evaluation = gateway.can_access(grant.id, subject="demo-user", permission="stream.read")
    if evaluation.decision != ExposureDecision.ALLOW:
        raise RuntimeError(evaluation.reason)

    print("OK: inventory registry and exposure gateway MVP validated")
    print(f"grant={grant.id} expires_at={grant.expires_at.isoformat()} direct_device_access={grant.direct_device_access}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
