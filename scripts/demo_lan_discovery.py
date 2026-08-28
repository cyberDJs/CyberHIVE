#!/usr/bin/env python3
from cyberhive_core.lan_discovery import (
    HandshakeResponse,
    LANDiscoveryRegistry,
    LANEnrollmentCoordinator,
    NodeAdvertisement,
)


def main() -> int:
    discovery = LANDiscoveryRegistry(ttl_seconds=120)
    record = discovery.observe(
        NodeAdvertisement(
            proposed_node_id="node.gamma",
            endpoints=("10.0.0.42:9443", "node-gamma.local:9443"),
            capabilities=("model.prewarm", "cache.prime"),
            labels={"room": "studio"},
            metadata={"transport": "mdns-simulated"},
        )
    )
    coordinator = LANEnrollmentCoordinator(discovery=discovery, handshake_ttl_seconds=300)
    handshake = coordinator.issue_handshake("node.gamma")
    response = HandshakeResponse.sign(
        handshake=handshake,
        public_key="ssh-ed25519 cyberhive-node-gamma",
        nonce="gamma-nonce-1",
        capabilities=("model.prewarm", "cache.prime"),
    )
    decision = coordinator.complete_handshake(response)
    challenge = handshake.public_challenge()
    print(f"discovery: {record.status.value} node={record.proposed_node_id} endpoints={','.join(record.advertisement.endpoints)}")
    print(f"challenge: {challenge['id']} token={challenge['bootstrap_token_id']} secret_redacted={'bootstrap_secret' not in challenge}")
    print(f"enrollment: {decision.status.value} node={decision.identity.node_id if decision.identity else '-'}")
    refreshed = discovery.require("node.gamma")
    print(f"record: {refreshed.status.value} identity={refreshed.enrolled_identity_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
