# Install Patch 016

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_016_lan_discovery_enrollment_handshake_mvp.zip
cd cyberhive_patch_016_lan_discovery_enrollment_handshake_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Then validate from the target repo:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_lan_discovery_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_lan_discovery.py
```
