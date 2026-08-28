# Install Patch 004

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_004_data_fabric_mvp.zip
cd cyberhive_patch_004_data_fabric_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Then validate:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_data_fabric_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_data_fabric.py
```

With commit:

```bash
cd "$HOME/Downloads/cyberhive_patch_004_data_fabric_mvp"
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI" --commit
```
