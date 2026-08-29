# Install Patch 019 — Reliable Node Delivery Queue MVP

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_019_reliable_delivery_queue_mvp.zip
cd cyberhive_patch_019_reliable_delivery_queue_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Verify:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_node_delivery_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_node_delivery.py
```
