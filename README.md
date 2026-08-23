# CyberHIVE AI

Open-source, local-first platform for operating, orchestrating and managing AI models, agents, tools, skills and compute nodes on owned hardware, servers and optional cloud infrastructure.

## Status

Architecture / bootstrap phase. Initial reference target: headless Linux host with NVIDIA RTX 3070, web administration and optional kiosk mode.

## Start here

1. Read `docs/PROJECT_CONTEXT.md`.
2. Read `AGENTS.md` before making code or infrastructure changes.
3. Use `docs/adr/` for architectural decisions.
4. Keep source design media in Google Drive and approved exports in `assets/`.
5. Keep reusable ChatGPT workflows in `skills/`.

## Repository map

- `docs/` — product, architecture, security, roadmap and runbooks
- `skills/` — reusable CyberHIVE ChatGPT skills
- `assets/` — approved repository-safe visual assets
- `src/` — application code
- `tests/` — automated tests
- `infra/` — deployment/IaC
- `scripts/` — project automation
