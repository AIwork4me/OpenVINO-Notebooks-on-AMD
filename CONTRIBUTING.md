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
.venv-cpu/bin/python -m pytest          # must pass
ruff check .              # must pass
```

- Commits: conventional style (`feat:`, `fix:`, `docs:`, `data:`).
- Add/extend tests for harness changes.
- For validation data: attach evidence dirs or explain why they are omitted.

## Reporting compatibility results

Open an issue with: workload id, hardware (CPU/GPU), software versions
(`python -m ov_amd doctor` output), **compatibility outcome** (VERIFIED /
VERIFIED_WITH_LIMITATIONS / BLOCKED_* / FAILED_COMPATIBILITY — see
`docs/validation-policy.md`), and logs. We will reproduce before updating the
matrix. Templates: compatibility report, compatibility issue, blocked
environment, upstream candidate (`.github/ISSUE_TEMPLATE/`).

## What you can contribute

- **New AMD CPU results** — run a workload on your Ryzen hardware with the
  harness (`python -m ov_amd run <id> --device cpu`), attach the evidence dir.
- **New AMD hardware** — `python -m ov_amd doctor` output + a representative
  verified workload; platform attribution is recorded per row.
- **ROCm twins** — add `workloads/<id>/rocm/run.py` (prints
  `TWIN_RESULT={json}` with `ok` + `hip`), run on Radeon; twin levels
  (EXACT/WORKLOAD/CONCEPT) decide what comparisons are publishable.
- **Failure reproductions** — minimize a FAILED_COMPATIBILITY row into a
  standalone script (see `reports/upstream/`).
- **Upstream issues** — only with a minimized repro; never speculative.

## Key distinction (read before filing)

A gated model, network timeout, missing CLI, or truncated download is
**blocked**, not an AMD/OpenVINO compatibility failure. If the environment
was valid and the OpenVINO runtime itself failed, it is a compatibility
issue. The issue templates encode this; the matrix enforces it
(`ov_amd/outcomes.py`).
