# ADR-0005: Model Swarm peer identity and authorization

- Status: Proposed
- Date: 2026-08-23
- Decision owners: CyberHIVE maintainers

## Context

Model Swarm exchanges model chunks directly between nodes. LAN reachability is not identity, chunk integrity does not imply authorization, and a compromised or unknown node must not gain access to every model simply because it can contact a peer.

CyberHIVE must remain local-first and usable offline without introducing an external identity platform, distributed database or SaaS dependency.

## Decision

CyberHIVE Model Swarm v0.1 uses a local installation CA as its offline trust root. Manual enrollment issues Ed25519 node certificates whose URI SAN carries a SPIFFE-compatible identity of the form `spiffe://cyberhive.local/node/<node-id>`. This does not require SPIRE or another identity service.

Peer data traffic uses TLS 1.3 mutual authentication. A secure server requires a client certificate signed by the configured CyberHIVE CA. A secure client verifies the server certificate and hostname/IP against the same configured trust root.

Authentication and authorization are separate. Local authorization policy binds:

- whole-artifact SHA-256;
- the approved chunk hashes belonging to that artifact;
- the node identities allowed to retrieve it.

A valid node certificate therefore does not grant blanket access to the CAS. Requests are scoped to `/v1/artifacts/<artifact-sha256>/chunks/<chunk-sha256>` and must pass both identity and policy checks.

For the local-first v0.1 trust model, operator registration of a manifest into the local authorization policy is the publisher-authenticity gate: an arbitrary remote manifest is not authority merely because it is syntactically valid. Remote/public catalogs will require signed manifests or an equivalent trusted registry before they can become an authority source.

The development HTTP server is restricted to loopback. LAN serving requires the explicit `secure-serve` path. Secure serving applies per-peer concurrency and token-bucket request limits.

Private keys are created outside Git by operator-selected identity directories, mode `0600`, and existing key files are never overwritten automatically.

## Consequences

Positive:
- offline node identity and trust work without a cloud service;
- unknown nodes fail at the TLS boundary;
- authenticated but unauthorized nodes fail at the artifact policy boundary;
- private model authorization is independent of network topology;
- node private keys are persistent but not stored in repository configuration;
- the design uses Go standard-library cryptography only.

Negative:
- v0.1 enrollment is manual CA issuance rather than an interactive one-time enrollment protocol;
- CA private-key custody becomes security-critical;
- certificate revocation/rotation is not yet automated;
- policy generation currently enumerates artifact chunks;
- remote catalog authenticity still needs a signed-manifest or trusted-registry design before public federation.

## Rejected alternatives

- Trust any LAN peer: rejected because network position is not identity.
- Bearer token as primary node identity: rejected because long-lived shared secrets are harder to scope, rotate and bind to transport identity.
- Custom cryptographic protocol: rejected because TLS 1.3 and X.509 already provide the required authenticated encrypted channel.
- Mandatory SPIRE/external PKI: rejected for v0.1 because it violates the minimal offline single-node requirement.
- Public DHT enrollment: rejected because discovery must not imply trust or authorization.

## Migration and rollback

The secure transport is additive. Existing loopback-only development transport remains available for isolated testing. Removing the security branch returns to the Model Swarm core without changing CAS content or manifest identity.

Future automated enrollment may issue certificates under the same node identity scheme. Future signed manifests can be added without changing chunk hashes or the peer transport contract.
