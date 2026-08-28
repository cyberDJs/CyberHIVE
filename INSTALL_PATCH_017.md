# Install Patch 017 — Secure Channel MVP

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_017_secure_channel_mvp.zip
cd cyberhive_patch_017_secure_channel_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Validate:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_secure_channel_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_secure_channel.py
```

Commit:

```bash
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
git add .
git commit -m "Add CyberHIVE Secure Channel MVP"
```
