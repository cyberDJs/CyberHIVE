import unittest
from datetime import UTC, datetime, timedelta

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


class InventoryExposureMvpTests(unittest.TestCase):
    def make_registry(self):
        registry = InventoryRegistry()
        registry.add(
            InventoryItem(
                id="camera.frontdoor",
                kind="camera",
                name="Front door camera",
                indexing=IndexingMode.NON_INDEXED,
                access=AccessMode.GATED,
                exposure=ExposureMode.PRIVATE,
                sensitivity=Sensitivity.SENSITIVE,
                capabilities=[Capability("video.stream", ("stream.read",)), Capability("video.snapshot", ("snapshot.read",))],
            )
        )
        return registry

    def test_inventory_rejects_secret_indexing(self):
        item = InventoryItem(
            id="secret.doc",
            kind="document",
            name="Secret doc",
            indexing=IndexingMode.INDEXED,
            sensitivity=Sensitivity.SECRET,
        )
        with self.assertRaises(ValueError):
            item.validate()

    def test_private_camera_can_get_authenticated_scoped_grant(self):
        gateway = ExposureGateway(self.make_registry())
        grant = gateway.create_grant(
            ExposureRequest(
                resource_id="camera.frontdoor",
                subject="petr",
                permissions=("stream.read",),
                ttl_seconds=600,
                reason="temporary yard check",
            )
        )
        result = gateway.can_access(grant.id, subject="petr", permission="stream.read")
        self.assertEqual(result.decision, ExposureDecision.ALLOW)
        self.assertFalse(grant.direct_device_access)
        self.assertFalse(grant.allow_download)

    def test_camera_download_is_denied_by_default(self):
        gateway = ExposureGateway(self.make_registry())
        with self.assertRaises(PermissionError):
            gateway.create_grant(
                ExposureRequest(
                    resource_id="camera.frontdoor",
                    subject="petr",
                    permissions=("stream.read",),
                    allow_download=True,
                )
            )

    def test_expired_grant_is_denied(self):
        gateway = ExposureGateway(self.make_registry())
        grant = gateway.create_grant(
            ExposureRequest(
                resource_id="camera.frontdoor",
                subject="petr",
                permissions=("stream.read",),
                ttl_seconds=1,
            )
        )
        future = datetime.now(UTC) + timedelta(seconds=5)
        result = gateway.can_access(grant.id, subject="petr", permission="stream.read", now=future)
        self.assertEqual(result.decision, ExposureDecision.DENY)


if __name__ == "__main__":
    unittest.main()
