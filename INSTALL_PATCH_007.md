# Install Patch 007

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_patch_007_observations_forecasting_mvp.zip
cd cyberhive_patch_007_observations_forecasting_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

## Verify

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_observations_forecasting_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_observations_forecasting.py
```

## Commit

```bash
git add .
git commit -m "Add CyberHIVE Observations and Forecasting MVP"
```
