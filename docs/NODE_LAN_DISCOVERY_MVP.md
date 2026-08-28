# CyberHIVE LAN Discovery & Enrollment Handshake MVP

Patch 016 adds a safe local discovery and enrollment handshake layer.

Discovery is not identity. A discovered node is only an untrusted candidate until it completes the HMAC-backed enrollment proof handled by `EnrollmentAuthority` from Patch 014.

## Components

- `NodeAdvertisement` — untrusted local announcement.
- `LANDiscoveryRegistry` — in-memory discovery registry with TTL and stale detection.
- `EnrollmentHandshake` — short-lived challenge that redacts the bootstrap secret from its public form.
- `HandshakeResponse` — signed node response.
- `LANEnrollmentCoordinator` — connects discovery to node enrollment.

## Security invariants

- Public endpoints are rejected by default.
- Discovery does not create node identity.
- A node cannot claim capabilities beyond its advertised/allowed set.
- The public challenge never exposes the bootstrap secret.
- Expired handshakes are denied.
- Completion delegates proof verification to the existing enrollment authority.

## Non-goals

- Real mDNS or UDP multicast.
- QR-code provisioning.
- mTLS or remote attestation.
- SSH, shell, Docker or remote execution.
- Persistent registry storage.
