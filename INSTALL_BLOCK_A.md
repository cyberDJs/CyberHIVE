# Install Block A — Worker Runtime Loop

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_block_a_worker_runtime_mvp.zip
cd cyberhive_block_a_worker_runtime_mvp
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Verify:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
```
