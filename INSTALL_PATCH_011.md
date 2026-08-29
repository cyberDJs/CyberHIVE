# Install Patch 011 — Policy & Governance MVP

From the directory containing this patch:

```bash
./apply_to_repo.sh "/path/to/CyberHIVE AI"
```

Then verify:

```bash
cd "/path/to/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_policy_governance_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_policy_governance.py
```

Commit:

```bash
git add .
git commit -m "Add CyberHIVE Policy and Governance MVP"
```
