# ADR-0007 — Live USB Real Build Gate

## Status

Proposed

## Context

CyberHIVE now has a Live USB skeleton and a repository-only build dry-run gate.

The next durable boundary is the first real image build. That boundary must be explicit because image builds create binary artifacts that can later be written to removable media and booted on hardware.

A build artifact is not runtime verification and does not prove host-disk safety.

## Decision

The first real CyberHIVE Live USB image build must be a separate governed gate after the dry-run gate.

The real build gate must bind authorization to:

- source commit,
- build candidate path,
- output directory,
- builder identity label,
- allowed operation class,
- expected artifact evidence.

The build gate may create an image artifact candidate and evidence files only when separately authorized.

USB writing, boot smoke testing, runtime verification, DevBridge/MCP exposure and ADR acceptance remain separate gates.

## Consequences

Positive:

- binary artifact creation is separated from repository planning,
- USB writing cannot be smuggled into an image build,
- runtime claims remain evidence-bound,
- future boot tests can bind to image hashes.

Tradeoffs:

- at least one additional work block before a bootable USB is tested,
- operators must capture evidence before promotion,
- build success alone is intentionally insufficient.

## Verification

For this proposed ADR, verification is limited to repository plan checks.

For a future accepted real build gate, verification must include:

- exact source commit,
- image SHA-256,
- manifest SHA-256,
- build log SHA-256,
- explicit negative claims for USB write and boot/runtime verification,
- separate boot smoke test evidence before runtime claims.

## Notes

This ADR remains proposed until explicitly accepted by project decision authority.

The file existing in the repository is not acceptance.
