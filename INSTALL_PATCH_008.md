# Install Patch 008 — Scheduler + Router MVP

From the directory where this patch was unzipped:

```bash
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Then verify manually:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_scheduler_router_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_scheduler_router.py
```

Commit:

```bash
git add .
git commit -m "Add CyberHIVE Scheduler and Router MVP"
```
