# Threat Model — Seed

## Assets

Model files, prompts/data, credentials, API keys, node identities, configuration, audit records and compute capacity.

## Trust boundaries

Browser <-> controller; controller <-> worker; worker <-> model runtime; CyberHIVE <-> connectors/cloud; package/update source <-> installed system.

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

Threat modeling evolves with each architectural decision and public interface.
