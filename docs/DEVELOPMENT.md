# Development

Prefer a modular monolith until measured scaling or isolation constraints require decomposition. New dependencies require purpose, license, maintenance status and rollback consideration.

## Change flow

1. Read context and relevant ADRs.
2. State problem and acceptance criteria.
3. Make the smallest coherent change.
4. Run targeted tests and static checks.
5. Update docs/ADR when behavior or architecture changes.
6. Record security/compatibility impact.

## Model Swarm Go checks

From the repository root run:

```bash
go vet ./...
go test -race ./...
go build ./cmd/cyberhive
```

The current HTTP peer transport is development-only. Keep it bound to localhost or a controlled test network until peer identity and artifact authorization are implemented.

## M0 Python checks

The first benchmark tooling intentionally uses the Python standard library only.

From the repository root run:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/collect_host_facts.py scripts/benchmark_openai.py
```

Host-facts smoke check:

```bash
python3 scripts/collect_host_facts.py
```

A machine without NVIDIA hardware may report `nvidia-smi not found`; that is a valid collector result, not a test failure. The RTX 3070 acceptance test must run on the actual reference node.
