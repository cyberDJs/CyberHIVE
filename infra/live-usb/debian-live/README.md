# Debian Live Candidate

## Status

Candidate only. Not accepted as final base image yet.

## Why this candidate exists

Debian live-build is a practical first path for a bootable CyberHIVE Live USB because it is understandable, conventional, and easy to inspect.

The first objective is not perfection. The first objective is a bootable, safe, branded CyberHIVE runtime artifact.

## Candidate package groups

Initial package groups to evaluate:

- base live system
- networking tools
- hardware inventory tools
- Python runtime
- Git
- lightweight local API runtime
- text UI / role selector dependencies
- optional browser or kiosk surface
- logging and evidence tools

## Open decisions

- Debian release target
- persistence/overlay method
- desktopless vs minimal browser/kiosk session
- systemd unit layout
- boot splash implementation
- role selector implementation
- image signing/hash policy
- Secure Boot support target

## Rejection criteria

Reject or defer this candidate if it cannot support:

- safe no-host-disk-write default,
- reproducible-enough image builds,
- clear persistent overlay policy,
- predictable network behavior,
- simple CI validation,
- future branded runtime surface.
