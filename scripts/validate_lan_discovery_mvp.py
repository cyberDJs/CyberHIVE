#!/usr/bin/env python3
from cyberhive_core.lan_discovery import (
    HandshakeResponse,
    LANDiscoveryRegistry,
    LANEnrollmentCoordinator,
    NodeAdvertisement,
)


def main() -> int:
    discovery = LANDiscoveryRegistry()
    record = discovery.observe(
        NodeAdvertisement(
            proposed_node_id="node.beta",
            endpoints=("192.168.1.23:9443", "node-beta.local:9443"),
            capabilities=("model.prewarm", "data.move", "cache.prime"),
            labels={"role": "worker"},
        )
    )
    assert record.status.value == "seen", record
    coordinator = LANEnrollmentCoordinator(discovery=discovery)
    handshake = coordinator.issue_handshake("node.beta", allowed_capabilities=("model.prewarm", "cache.prime"))
    public = handshake.public_challenge()
    assert "bootstrap_secret" not in public
    response = HandshakeResponse.sign(
        handshake=handshake,
        public_key="ssh-ed25519 cyberhive-node-beta",
        nonce="nonce-beta-1",
        capabilities=("model.prewarm",),
        labels={"zone": "lab"},
    )
    decision = coordinator.complete_handshake(response)
    assert decision.approved, decision.as_dict()
    session, token = coordinator.authority.registry.issue_session("node.beta")
    assert coordinator.authority.registry.verify_session(session.id, "node.beta", token)
    print("OK: LAN Discovery & Enrollment Handshake MVP validation passed")
    print(f"discovered={record.proposed_node_id} handshake={handshake.id} identity={decision.identity.node_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
