# Install Block J — PATCH_028

Apply this package on top of PR #21 head after PATCH_027.

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_block_j_block_i_p1_repair.zip
cd cyberhive_block_j_block_i_p1_repair
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Verify from the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/validate_node_reconciliation_mvp.py
PYTHONPATH=src python3 scripts/validate_secure_node_gateway_mvp.py
PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
PYTHONPATH=src python3 scripts/demo_node_reconciliation.py
```

Commit expected files:

```bash
git add \
  src/cyberhive_core/node_delivery.py \
  src/cyberhive_core/node_reconciliation.py \
  src/cyberhive_core/secure_node_gateway.py \
  tests/test_node_delivery_mvp.py \
  tests/test_node_reconciliation_mvp.py \
  tests/test_secure_node_gateway_mvp.py \
  docs/NODE_DELIVERY_MVP.md \
  docs/NODE_RECONCILIATION_MVP.md \
  docs/NODE_SECURE_GATEWAY_MVP.md \
  docs/CODEX_BLOCK_I_P1_REPAIR.md \
  PATCH_028.md \
  INSTALL_BLOCK_J.md

git commit -m "Fix Codex Block I P1 findings for PR 21"
git push origin caser/block-b-canonical-sync
```
