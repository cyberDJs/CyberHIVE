# Install Patch 009 — Integration Orchestrator MVP

From the directory containing this patch:

```bash
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Then verify:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_integration_orchestrator_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_integration_orchestrator.py
```

Commit:

```bash
git add .
git commit -m "Add CyberHIVE Integration Orchestrator MVP"
```
