# Contributing

Thanks for improving **OpenVINO Notebooks on AMD**!

## Ground rules

1. **Evidence or it didn't happen.** Any status/benchmark claim must come from
   a reproducible run and land with its evidence (see `docs/validation-policy.md`).
2. Never hand-edit generated files (`catalog/compatibility.*`, README status
   block, `reports/*`). Change the harness or state and regenerate with
   `python -m ov_amd report`.
3. Keep upstream notebooks unmodified in this repo — we execute them from the
   pinned clone. Patches are declarative and documented
   (`docs/adding-a-workload.md`).

## Workflow

```bash
uv venv .venv-cpu --python 3.12
uv pip install --python .venv-cpu/bin/python -e ".[dev]"
python -m pytest          # must pass
ruff check .              # must pass
```

- Commits: conventional style (`feat:`, `fix:`, `docs:`, `data:`).
- Add/extend tests for harness changes.
- For validation data: attach evidence dirs or explain why they are omitted.

## Reporting compatibility results

Open an issue with: workload id, hardware (CPU/GPU), software versions
(`python -m ov_amd doctor` output), status, and logs. We will reproduce before
updating the matrix.
