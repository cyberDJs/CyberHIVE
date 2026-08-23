---
name: cyberhive-repo-engineer
description: Implement and review changes in the CyberHIVE repository with repository-aware planning, minimal diffs, tests, documentation, security impact and rollback notes. Use for GitHub issues, code changes, bug fixes, refactors, CI changes, configuration changes, pull requests and repository maintenance related to CyberHIVE. Use the GitHub connector when repository state is needed and never claim a test or command succeeded unless it actually ran.
---

# CyberHIVE Repo Engineer

Inspect `AGENTS.md`, project context, relevant ADRs, component README, tests and CI before modifying code.

## Workflow

1. Identify the requested behavior and acceptance criteria.
2. Inspect existing implementation before proposing new structure.
3. Prefer the smallest coherent diff.
4. Preserve public interfaces unless change is intentional and documented.
5. Add or update tests for behavioral changes.
6. Run the narrowest useful test/check set, then broader checks when justified.
7. Update documentation and ADRs in the same change when required.
8. Report security, compatibility, operational and rollback impact.

## Guardrails

- Never invent repository files, CI results or command output.
- Never commit secrets.
- Require explicit confirmation for destructive or externally visible actions.
- Do not introduce infrastructure complexity without evidence.
