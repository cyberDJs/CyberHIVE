# CyberHIVE Agent Instructions

## Required reading

Before modifying the project, inspect:

1. `docs/PROJECT_CONTEXT.md`
2. `docs/ARCHITECTURE.md`
3. relevant ADR records
4. relevant component README
5. current tests and CI configuration

## Working rules

- Prefer the smallest coherent change.
- Do not silently redesign unrelated components.
- Do not claim a command or test succeeded unless it was executed.
- Never commit credentials, tokens, private keys or production secrets.
- Destructive operations require a dry-run, rollback plan and confirmation.
- Add or update tests for behavioral changes.
- Keep components replaceable through documented interfaces.
- Record significant architectural changes as ADRs.
- Update documentation in the same change as implementation.
- Do not introduce Kubernetes, distributed messaging or extra databases without measurable justification.

## Pull request output

Every proposed change must summarize problem, chosen solution, changed components, tests, security impact, compatibility impact, rollback and unresolved risks.
