# CyberHIVE Runtime Branding

## Principle

Branding is part of the CyberHIVE runtime experience.

The live USB must not feel like a generic Linux rescue image with a CyberHIVE sticker. It should communicate the product model directly at boot and runtime:

- live USB,
- peer-to-peer fabric,
- local-first,
- aggressive caching,
- weak-network resilience,
- failure-aware scheduling,
- multi-platform participation.

## Visual language

Core motifs:

- hexagon / hive cells,
- connected peer nodes,
- dark high-contrast surfaces,
- cyan, teal and cool-blue highlights,
- sharp minimal icons,
- clear status colors,
- compact technical typography.

## Required branded surfaces

### Boot splash

Text elements:

- `CyberHIVE Live USB`
- `Peer-to-peer AI fabric`
- `Local-first | Resilient | Private | Portable`

### Boot role selector

Title:

- `CyberHIVE — Select Boot Role`

Roles:

- Controller + Worker
- Worker Only
- DevBridge Mode
- Offline Diagnostics
- Rescue / Hardware Inventory

### Runtime dashboard

Header indicators:

- Fabric Status
- Local-first
- Multi-platform
- Peer-to-peer
- Weak Net Mode
- Cache Aggressive
- Failure-Aware

Dashboard cards:

- Node Status
- Hardware Inventory
- Capability Map
- Cache Health
- Network Health
- DevBridge / MCP
- Topology
- Cluster Peers
- Logs / Evidence

## Device icon language

Runtime topology should be able to represent heterogeneous peers:

- desktop,
- laptop,
- phone,
- tablet,
- watch,
- NAS,
- edge box,
- server,
- cloud/VPS.

Icons must not imply that only powerful GPU machines matter.

## Messaging

Preferred short phrases:

- `Any device, any role.`
- `Boot. Join. Contribute.`
- `No central server required.`
- `Speed where it matters.`
- `Built for weak networks.`
- `Smart. Adaptive. Reliable.`
- `Your AI fabric. In your pocket.`

Avoid:

- platform narrowing,
- GPU-only language,
- cloud-first framing,
- vague AI hype,
- hiding safety boundaries.

## First concept asset

A concept image was generated for the boot splash, role selector and runtime dashboard direction. It should be treated as visual guidance, not as an implementation asset until exported, reviewed and committed explicitly.

Future repository-safe exports should live under:

```text
assets/brand/runtime/
```
