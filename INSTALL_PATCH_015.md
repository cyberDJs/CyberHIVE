# Install Patch 015

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_015_node_heartbeat_capability_sync_mvp.zip
cd cyberhive_patch_015_node_heartbeat_capability_sync_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Verify:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_node_heartbeat_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_node_heartbeat.py
```

Commit:

```bash
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
git add .
git commit -m "Add CyberHIVE Node Heartbeat and Capability Sync MVP"
```
