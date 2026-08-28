# Install Patch 018 — Secure Node Gateway MVP

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_018_secure_node_gateway_mvp.zip
cd cyberhive_patch_018_secure_node_gateway_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Verify:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_secure_node_gateway_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_secure_node_gateway.py
```
