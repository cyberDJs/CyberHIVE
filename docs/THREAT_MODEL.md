# Threat Model — Seed

## Assets

Model files, prompts/data, credentials, API keys, node identities, configuration, audit records and compute capacity.

## Trust boundaries

Browser <-> controller; controller <-> worker; worker <-> model runtime; CyberHIVE <-> connectors/cloud; package/update source <-> installed system; Model Swarm peer <-> Model Swarm peer.

## Initial threats

- unauthorized node enrollment
- credential theft
- malicious model/skill package
- exposed administration API
- supply-chain compromise
- privilege escalation through runtime/container integration
- lateral movement from a compromised worker
- resource exhaustion / compute theft
- unsafe update leaving node unavailable

## Model Swarm threats and controls

| Threat | v0.1 control | Residual risk |
| --- | --- | --- |
| Unknown LAN host requests model chunks | TLS 1.3 mTLS with CA-issued node identity | CA compromise or mis-issued certificate |
| Enrolled node requests private artifact | Explicit artifact/chunk ACL by node ID | Policy administration mistakes |
| Peer serves corrupted bytes | Per-chunk SHA-256 plus whole-artifact SHA-256 | Hash algorithm migration remains future work |
| Peer floods chunk endpoint | Per-peer token bucket and concurrency limit | Distributed flooding from many valid identities |
| Private key is accidentally committed | Identity files live outside Git, key mode `0600`, create-exclusive writes | Host compromise can still steal local keys |
| Discovery is mistaken for trust | Discovery and authorization are separate interfaces | Operator may still grant overly broad policy |
| Remote manifest attempts to redefine trusted content | Local operator policy binds artifact SHA and chunk set | Public federation needs signed manifests/trusted registry |
| Development server is exposed on LAN | Plain `serve` is restricted to loopback | Local host users can still access development endpoint |

Certificate revocation, automated rotation and public-federation trust are intentionally unresolved and must be designed before Internet-facing swarm operation.

Threat modeling evolves with each architectural decision and public interface.
