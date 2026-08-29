from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from cyberhive_core.node_identity import (
    BootstrapToken,
    EnrollmentAuthority,
    EnrollmentRequest,
    EnrollmentStatus,
    NodeIdentity,
    NodeIdentityRegistry,
    TrustState,
    compute_enrollment_proof,
    public_key_fingerprint,
    token_secret_digest,
)
from cyberhive_core.node_agent import AgentActionType


class NodeIdentityMvpTests(unittest.TestCase):
    def test_bootstrap_token_enrolls_node_once(self) -> None:
        authority = EnrollmentAuthority()
        token, secret = authority.create_bootstrap_token()
        request = authority.build_request(
            proposed_node_id="node.gamma",
            public_key="ssh-ed25519 AAAATEST node.gamma",
            token_id=token.id,
            token_secret=secret,
            capabilities=("model.prewarm", "data.move"),
            labels={"zone": "lab"},
        )
        decision = authority.evaluate(request)
        self.assertEqual(decision.status, EnrollmentStatus.APPROVED)
        self.assertIsNotNone(decision.identity)
        self.assertEqual(decision.identity.node_id, "node.gamma")
        self.assertEqual(authority.token_status(token.id)["uses"], 1)

        replay = authority.evaluate(request)
        self.assertEqual(replay.status, EnrollmentStatus.DENIED)

    def test_invalid_proof_is_denied(self) -> None:
        authority = EnrollmentAuthority()
        token, _secret = authority.create_bootstrap_token()
        request = EnrollmentRequest(
            proposed_node_id="node.bad",
            public_key="ssh-ed25519 BAD",
            bootstrap_token_id=token.id,
            nonce="n1",
            proof="not-valid",
        )
        decision = authority.evaluate(request)
        self.assertEqual(decision.status, EnrollmentStatus.DENIED)
        self.assertIn("invalid", decision.reason)

    def test_expired_token_is_denied(self) -> None:
        registry = NodeIdentityRegistry()
        authority = EnrollmentAuthority(registry)
        secret = "expired-secret"
        token = BootstrapToken(
            id="bt_expired",
            secret_digest=token_secret_digest(secret),
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        authority._tokens[token.id] = token  # direct injection for deterministic test
        request = authority.build_request(
            proposed_node_id="node.old",
            public_key="ssh-ed25519 OLD",
            token_id=token.id,
            token_secret=secret,
        )
        decision = authority.evaluate(request)
        self.assertEqual(decision.status, EnrollmentStatus.DENIED)
        self.assertIn("expired", decision.reason)

    def test_registry_session_requires_enrolled_identity(self) -> None:
        registry = NodeIdentityRegistry()
        identity = registry.register(
            NodeIdentity(
                node_id="node.session",
                public_key_fingerprint=public_key_fingerprint("ssh-ed25519 SESSION"),
                capabilities=("health",),
            )
        )
        grant, token = registry.issue_session(identity.node_id, ttl_seconds=60)
        self.assertTrue(registry.verify_session(grant.id, identity.node_id, token))
        self.assertFalse(registry.verify_session(grant.id, identity.node_id, "wrong"))

        registry.revoke(identity.node_id)
        self.assertFalse(registry.verify_session(grant.id, identity.node_id, token))
        with self.assertRaises(Exception):
            registry.issue_session(identity.node_id)


    def test_quarantine_invalidates_existing_sessions(self) -> None:
        registry = NodeIdentityRegistry()
        identity = registry.register(
            NodeIdentity(node_id="node.session.q", public_key_fingerprint=public_key_fingerprint("ssh-ed25519 SESSIONQ"))
        )
        grant, token = registry.issue_session(identity.node_id, ttl_seconds=60)
        self.assertTrue(registry.verify_session(grant.id, identity.node_id, token))

        registry.quarantine(identity.node_id, "suspicious traffic")

        self.assertFalse(registry.verify_session(grant.id, identity.node_id, token))

    def test_quarantine_and_restore(self) -> None:
        registry = NodeIdentityRegistry()
        identity = registry.register(
            NodeIdentity(node_id="node.q", public_key_fingerprint=public_key_fingerprint("ssh-ed25519 Q"))
        )
        registry.quarantine("node.q", "unexpected heartbeat signature")
        self.assertEqual(identity.trust_state, TrustState.QUARANTINED)
        self.assertFalse(identity.is_allowed())
        identity.restore()
        self.assertEqual(identity.trust_state, TrustState.ENROLLED)

    def test_duplicate_fingerprint_for_different_node_is_denied(self) -> None:
        registry = NodeIdentityRegistry()
        fp = public_key_fingerprint("ssh-ed25519 SAME")
        registry.register(NodeIdentity(node_id="node.one", public_key_fingerprint=fp))
        with self.assertRaises(Exception):
            registry.register(NodeIdentity(node_id="node.two", public_key_fingerprint=fp))

    def test_identity_to_node_descriptor_maps_capabilities_to_allowed_actions(self) -> None:
        identity = NodeIdentity(
            node_id="node.delta",
            public_key_fingerprint=public_key_fingerprint("ssh-ed25519 DELTA"),
            capabilities=("model.prewarm", "data.move", "cache.prime"),
            labels={"role": "worker"},
        )
        descriptor = identity.to_node_descriptor()
        self.assertEqual(descriptor.id, "node.delta")
        self.assertTrue(descriptor.supports_action(AgentActionType.PREWARM_MODEL))
        self.assertTrue(descriptor.supports_action(AgentActionType.DATA_MOVE))
        self.assertTrue(descriptor.supports_action(AgentActionType.CACHE_PRIME))
        self.assertEqual(descriptor.metadata["trust_state"], "enrolled")

    def test_compute_proof_is_stable_for_same_inputs(self) -> None:
        first = compute_enrollment_proof("node.x", "ssh-ed25519 X", "nonce", "bt_x", "secret")
        second = compute_enrollment_proof("node.x", "ssh-ed25519 X", "nonce", "bt_x", "secret")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
