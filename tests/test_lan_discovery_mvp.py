from datetime import datetime, timedelta, timezone
import unittest

from cyberhive_core.lan_discovery import (
    DiscoveryStatus,
    HandshakeResponse,
    LANDiscoveryError,
    LANDiscoveryRegistry,
    LANEnrollmentCoordinator,
    NodeAdvertisement,
    is_lan_address,
)
from cyberhive_core.node_identity import EnrollmentStatus


class LANDiscoveryMVPTests(unittest.TestCase):
    def test_lan_address_detection(self):
        self.assertTrue(is_lan_address("192.168.1.20:9443"))
        self.assertTrue(is_lan_address("http://node-alpha.local:9443/health"))
        self.assertTrue(is_lan_address("node-alpha:9443"))
        self.assertFalse(is_lan_address("8.8.8.8:9443"))
        self.assertFalse(is_lan_address("worker.example.com:9443"))

    def test_public_endpoint_is_rejected(self):
        registry = LANDiscoveryRegistry()
        record = registry.observe(NodeAdvertisement("node.bad", ("8.8.8.8:9443",), capabilities=("model.prewarm",)))
        self.assertEqual(record.status, DiscoveryStatus.REJECTED)
        self.assertIn("public-endpoint-rejected", record.findings)

    def test_discovery_refresh_increments_seen_count(self):
        registry = LANDiscoveryRegistry()
        first = registry.observe(NodeAdvertisement("node.alpha", ("192.168.1.2:9443",)))
        second = registry.observe(NodeAdvertisement("node.alpha", ("192.168.1.2:9443",), capabilities=("cache.prime",)))
        self.assertEqual(first.seen_count, 1)
        self.assertEqual(second.seen_count, 2)
        self.assertEqual(second.status, DiscoveryStatus.SEEN)

    def test_stale_record_is_listed_as_stale(self):
        now = datetime.now(timezone.utc)
        registry = LANDiscoveryRegistry(ttl_seconds=10)
        registry.observe(NodeAdvertisement("node.old", ("10.0.0.10:9443",), observed_at=now), now=now)
        records = registry.list_records(now=now + timedelta(seconds=11))
        self.assertEqual(records[0].status, DiscoveryStatus.STALE)

    def test_handshake_challenge_redacts_secret(self):
        registry = LANDiscoveryRegistry()
        registry.observe(NodeAdvertisement("node.beta", ("192.168.1.3:9443",), capabilities=("model.prewarm",)))
        coordinator = LANEnrollmentCoordinator(discovery=registry)
        handshake = coordinator.issue_handshake("node.beta")
        public = handshake.public_challenge()
        self.assertNotIn("bootstrap_secret", public)
        self.assertEqual(public["proposed_node_id"], "node.beta")
        self.assertEqual(registry.require("node.beta").status, DiscoveryStatus.HANDSHAKE_READY)

    def test_complete_handshake_enrolls_node(self):
        registry = LANDiscoveryRegistry()
        registry.observe(NodeAdvertisement("node.beta", ("192.168.1.3:9443",), capabilities=("model.prewarm", "cache.prime")))
        coordinator = LANEnrollmentCoordinator(discovery=registry)
        handshake = coordinator.issue_handshake("node.beta", allowed_capabilities=("model.prewarm",))
        response = HandshakeResponse.sign(
            handshake=handshake,
            public_key="ssh-ed25519 beta",
            nonce="n1",
            capabilities=("model.prewarm",),
        )
        decision = coordinator.complete_handshake(response)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.identity.node_id, "node.beta")
        self.assertEqual(decision.identity.capabilities, ("model.prewarm",))
        self.assertEqual(registry.require("node.beta").status, DiscoveryStatus.ENROLLED)

    def test_response_cannot_request_unadvertised_capability(self):
        registry = LANDiscoveryRegistry()
        registry.observe(NodeAdvertisement("node.beta", ("192.168.1.3:9443",), capabilities=("model.prewarm",)))
        coordinator = LANEnrollmentCoordinator(discovery=registry)
        with self.assertRaises(LANDiscoveryError):
            coordinator.issue_handshake("node.beta", allowed_capabilities=("data.move",))

    def test_response_cannot_exceed_handshake_allowance(self):
        registry = LANDiscoveryRegistry()
        registry.observe(NodeAdvertisement("node.beta", ("192.168.1.3:9443",), capabilities=("model.prewarm", "data.move")))
        coordinator = LANEnrollmentCoordinator(discovery=registry)
        handshake = coordinator.issue_handshake("node.beta", allowed_capabilities=("model.prewarm",))
        response = HandshakeResponse.sign(
            handshake=handshake,
            public_key="ssh-ed25519 beta",
            nonce="n1",
            capabilities=("model.prewarm", "data.move"),
        )
        decision = coordinator.complete_handshake(response)
        self.assertEqual(decision.status, EnrollmentStatus.DENIED)
        self.assertEqual(decision.reason, "response capabilities exceed handshake allowance")

    def test_wrong_node_id_is_denied(self):
        registry = LANDiscoveryRegistry()
        registry.observe(NodeAdvertisement("node.beta", ("192.168.1.3:9443",), capabilities=("model.prewarm",)))
        coordinator = LANEnrollmentCoordinator(discovery=registry)
        handshake = coordinator.issue_handshake("node.beta")
        response = HandshakeResponse.sign(
            handshake=handshake,
            public_key="ssh-ed25519 beta",
            nonce="n1",
            capabilities=("model.prewarm",),
        )
        tampered = HandshakeResponse(
            handshake_id=response.handshake_id,
            proposed_node_id="node.evil",
            public_key=response.public_key,
            nonce=response.nonce,
            proof=response.proof,
            capabilities=response.capabilities,
        )
        decision = coordinator.complete_handshake(tampered)
        self.assertEqual(decision.status, EnrollmentStatus.DENIED)
        self.assertEqual(decision.reason, "handshake node id mismatch")

    def test_expired_handshake_is_denied(self):
        now = datetime.now(timezone.utc)
        registry = LANDiscoveryRegistry()
        registry.observe(NodeAdvertisement("node.beta", ("192.168.1.3:9443",), capabilities=("model.prewarm",)), now=now)
        coordinator = LANEnrollmentCoordinator(discovery=registry, handshake_ttl_seconds=1)
        handshake = coordinator.issue_handshake("node.beta", now=now)
        response = HandshakeResponse.sign(
            handshake=handshake,
            public_key="ssh-ed25519 beta",
            nonce="n1",
            capabilities=("model.prewarm",),
        )
        decision = coordinator.complete_handshake(response, now=now + timedelta(seconds=2))
        self.assertEqual(decision.status, EnrollmentStatus.DENIED)
        self.assertEqual(decision.reason, "handshake expired")


if __name__ == "__main__":
    unittest.main()
