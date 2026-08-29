# Install Patch 014 — Node Enrollment & Identity MVP

From `~/Downloads`:

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_014_node_enrollment_identity_mvp.zip
cd cyberhive_patch_014_node_enrollment_identity_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Validate:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_node_identity_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_node_identity.py
```

Commit:

```bash
git add .
git commit -m "Add CyberHIVE Node Enrollment and Identity MVP"
```
