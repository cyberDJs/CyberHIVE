# Install Patch 005

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_005_data_mover_mvp.zip
cd cyberhive_patch_005_data_mover_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

## Validate

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_data_mover_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_data_mover.py
```

## Commit

```bash
git add .
git commit -m "Add CyberHIVE Data Mover MVP"
```
