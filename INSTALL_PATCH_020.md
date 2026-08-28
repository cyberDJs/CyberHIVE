# INSTALL PATCH 020

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_020_node_result_reconciliation_mvp.zip
cd cyberhive_patch_020_node_result_reconciliation_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Verify:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_node_reconciliation_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_node_reconciliation.py
```
