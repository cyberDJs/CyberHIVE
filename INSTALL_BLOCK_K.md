# Install Block K / PATCH_029

Apply from the repository root after PATCH_028 is already present.

```bash
cd "$HOME/Downloads/CyberHIVE AI"

cp -R "$HOME/Downloads/cyberhive_block_k_block_j_p1_repair/src" .
cp -R "$HOME/Downloads/cyberhive_block_k_block_j_p1_repair/tests" .
cp -R "$HOME/Downloads/cyberhive_block_k_block_j_p1_repair/docs" .
cp "$HOME/Downloads/cyberhive_block_k_block_j_p1_repair/PATCH_029.md" .
cp "$HOME/Downloads/cyberhive_block_k_block_j_p1_repair/INSTALL_BLOCK_K.md" .
```

## Verify

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/validate_node_reconciliation_mvp.py
PYTHONPATH=src python3 scripts/validate_secure_node_gateway_mvp.py
PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
PYTHONPATH=src python3 scripts/demo_node_reconciliation.py
```
