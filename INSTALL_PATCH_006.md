# Install Patch 006

From `~/Downloads`:

```bash
unzip -o cyberhive_patch_006_cache_reuse_mvp.zip
cd cyberhive_patch_006_cache_reuse_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Verify:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_cache_reuse_mvp.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_cache_reuse.py
```

Commit:

```bash
git add .
git commit -m "Add CyberHIVE Cache and Reuse Fabric MVP"
```
