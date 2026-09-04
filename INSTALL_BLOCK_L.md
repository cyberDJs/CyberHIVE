# INSTALL — Block L / PATCH_030

Apply on top of canonical main after PR #21:

```bash
cd "$HOME/Downloads"
unzip -o cyberhive_block_l_post_merge_hardening.zip
cd cyberhive_block_l_post_merge_hardening
./apply_to_repo.sh "$HOME/Downloads/CyberHIVE AI"
```

Verify:

```bash
cd "$HOME/Downloads/CyberHIVE AI"
PYTHONPATH=src python3 -m unittest \
  tests.test_worker_runtime_mvp \
  tests.test_resource_guard_mvp \
  tests.test_cache_reuse_mvp \
  tests.test_data_mover_mvp
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/validate_worker_runtime_block_a.py
PYTHONPATH=src python3 scripts/validate_cache_reuse_mvp.py
PYTHONPATH=src python3 scripts/validate_data_mover_mvp.py
PYTHONPATH=src python3 scripts/demo_worker_runtime_block_a.py
```

Commit only after verification. This install step does not authorize deploy or
push.
