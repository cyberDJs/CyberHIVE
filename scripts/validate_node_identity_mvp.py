#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.node_identity import EnrollmentAuthority, EnrollmentStatus


def main() -> None:
    authority = EnrollmentAuthority()
    token, secret = authority.create_bootstrap_token(ttl_seconds=300)
    request = authority.build_request(
        proposed_node_id="node.validate",
        public_key="ssh-ed25519 VALIDATE node.validate",
        token_id=token.id,
        token_secret=secret,
        capabilities=("health", "model.prewarm"),
        labels={"zone": "validation"},
    )
    decision = authority.evaluate(request)
    assert decision.status == EnrollmentStatus.APPROVED, decision.as_dict()
    assert decision.identity is not None
    grant, session_token = authority.registry.issue_session("node.validate")
    assert authority.registry.verify_session(grant.id, "node.validate", session_token)
    descriptor = decision.identity.to_node_descriptor()
    assert descriptor.id == "node.validate"
    print("OK: Node Enrollment & Identity MVP validation passed")


if __name__ == "__main__":
    main()
