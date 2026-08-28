#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.node_identity import EnrollmentAuthority


def main() -> None:
    authority = EnrollmentAuthority()
    token, secret = authority.create_bootstrap_token(ttl_seconds=900)
    request = authority.build_request(
        proposed_node_id="node.gamma",
        public_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGAMMA node.gamma",
        token_id=token.id,
        token_secret=secret,
        capabilities=("health", "model.prewarm", "data.move"),
        labels={"zone": "studio", "gpu": "rtx3070"},
        metadata={"agent_version": "mvp"},
    )
    decision = authority.evaluate(request)
    print(f"enrollment: {decision.status.value} reason={decision.reason}")
    if decision.identity:
        print(f"identity: {decision.identity.node_id} fp={decision.identity.public_key_fingerprint[:24]}...")
        descriptor = decision.identity.to_node_descriptor()
        print(f"descriptor: enabled={descriptor.enabled} healthy={descriptor.healthy} actions={','.join(descriptor.normalized_actions())}")
        grant, session_token = authority.registry.issue_session(decision.identity.node_id, ttl_seconds=600)
        print(f"session: {grant.id} active={authority.registry.verify_session(grant.id, decision.identity.node_id, session_token)}")
    print(f"token_uses: {authority.token_status(token.id)['uses']}")


if __name__ == "__main__":
    main()
