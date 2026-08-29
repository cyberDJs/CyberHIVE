#!/usr/bin/env python3
"""Small demo for Inventory + Exposure Gateway."""
from __future__ import annotations

from cyberhive_core import (
    AccessMode,
    Capability,
    ExposureGateway,
    ExposureMode,
    ExposureRequest,
    IndexingMode,
    InventoryItem,
    InventoryRegistry,
    Sensitivity,
)

registry = InventoryRegistry()
registry.add(
    InventoryItem(
        id="camera.frontdoor",
        kind="camera",
        name="Front Door Camera",
        indexing=IndexingMode.NON_INDEXED,
        access=AccessMode.GATED,
        exposure=ExposureMode.PRIVATE,
        sensitivity=Sensitivity.SENSITIVE,
        capabilities=[Capability("video.stream", ("stream.read",)), Capability("video.snapshot", ("snapshot.read",))],
        metadata={"location": "home/frontdoor"},
    )
)

gateway = ExposureGateway(registry)
grant = gateway.create_grant(
    ExposureRequest(
        resource_id="camera.frontdoor",
        subject="petr",
        permissions=("stream.read",),
        ttl_seconds=7200,
        reason="Temporary access to check the garden while away",
    )
)

print("resource:", registry.get("camera.frontdoor"))
print("grant:", grant)
print("access:", gateway.can_access(grant.id, subject="petr", permission="stream.read").decision.value)
