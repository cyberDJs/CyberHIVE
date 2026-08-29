# Node Enrollment & Identity MVP

## Purpose

CyberHIVE worker nodes must not be trusted just because they say they are
`node.alpha` or `node.beta`.

Patch 014 creates the first enrollment and identity layer between unknown local
machines and trusted CyberHIVE node agents.

## Flow

```text
Bootstrap token
  ↓
Enrollment request
  ↓
HMAC proof verification
  ↓
NodeIdentity
  ↓
Node session grant
  ↓
NodeAgent descriptor
```

## Trust states

- `pending` — known but not accepted yet; reserved for later manual approval.
- `enrolled` — allowed to receive sessions and participate.
- `quarantined` — temporarily blocked because something looks wrong.
- `revoked` — permanently blocked in the MVP.

## MVP boundaries

This patch does not implement:

- mTLS,
- certificate authority,
- remote attestation,
- TPM/Secure Enclave binding,
- persistent encrypted identity store,
- network enrollment service.

Those are later patches. This MVP defines the contracts and tests.

## Security invariants

- Bootstrap token cleartext secret is returned only at creation time.
- Stored token material is a digest used as the HMAC key.
- Enrollment request signs canonical node id, public key fingerprint, nonce and token id.
- Duplicate node ids are denied.
- Duplicate public key fingerprints across nodes are denied.
- Revoked nodes cannot receive sessions.
- Quarantined nodes cannot receive sessions until restored.

## Integration

A `NodeIdentity` can be converted into a `NodeDescriptor` for the Node Agent
layer. Capabilities map to allowed typed node actions:

| Identity capability | Node action |
|---|---|
| `model.prewarm` | `prewarm_model` |
| `data.move` | `data_move` |
| `cache.prime` | `cache_prime` |

