# Install Patch 013 — Node Agent & Action Dispatch MVP

From the folder containing this patch:

```bash
./apply_to_repo.sh "/path/to/CyberHIVE AI"
```

Validate:

```bash
cd "/path/to/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_node_agent_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_node_agent.py
```

Commit:

```bash
git add .
git commit -m "Add CyberHIVE Node Agent and Action Dispatch MVP"
```
