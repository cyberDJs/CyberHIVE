# Install Patch 012 — Approval Workflow MVP

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_012_approval_workflow_mvp.zip
cd cyberhive_patch_012_approval_workflow_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Validate:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_approval_workflow_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_approval_workflow.py
```

Commit:

```bash
git add .
git commit -m "Add CyberHIVE Approval Workflow MVP"
```
