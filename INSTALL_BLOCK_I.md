# Install Block I / Patch 027

From the extracted patch directory:

```bash
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Then verify:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/validate_node_reconciliation_mvp.py
PYTHONPATH=src python3 scripts/validate_secure_node_gateway_mvp.py
PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
```

Commit:

```bash
git add \
  src/cyberhive_core/secure_node_gateway.py \
  src/cyberhive_core/node_reconciliation.py \
  schemas/secure-node-gateway-receipt.schema.json \
  tests/test_secure_node_gateway_mvp.py \
  tests/test_node_reconciliation_mvp.py \
  scripts/validate_node_reconciliation_mvp.py \
  scripts/demo_node_reconciliation.py \
  docs/NODE_SECURE_GATEWAY_MVP.md \
  docs/NODE_RECONCILIATION_MVP.md \
  docs/CODEX_VERIFIED_SESSION_P1_REPAIR.md \
  PATCH_027.md \
  INSTALL_BLOCK_I.md

git commit -m "Fix Codex verified session P1 for PR 21"
git push origin caser/block-b-canonical-sync
```
