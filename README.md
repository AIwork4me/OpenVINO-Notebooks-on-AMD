# OpenVINO Notebooks on AMD

> **Validate and run OpenVINO Notebooks on AMD Ryzen CPUs, with matching ROCm-powered references for AMD Radeon GPUs.**

> **One AI workload. Two AMD paths.**

> **Pick a notebook. Pick an AMD device. Run.**

```text
OpenVINO Notebook
       |
 +-----+-----+
 |           |
Ryzen      Radeon
CPU         GPU
 |           |
OpenVINO    ROCm
 |           |
 +-----+-----+
       |
  Validation
```

This is **an AMD validation and ROCm companion project for [OpenVINO Notebooks](https://github.com/openvinotoolkit/openvino_notebooks)** — not a fork. Upstream notebooks are executed unmodified (or with documented, minimal patches) at a pinned upstream commit, on real AMD hardware, with machine-generated evidence for every claim.

- **Pillar A — Ryzen CPU validation:** which OpenVINO Notebooks actually run on AMD Ryzen CPUs?
- **Pillar B — Radeon ROCm twins:** the same AI workload through PyTorch/ROCm on AMD Radeon GPUs.
- **Pillar C — compatibility evidence database:** every notebook carries a status, an evidence directory, and a failure category.

<!-- generated:compatibility begin -->
**171 notebooks catalogued** — CPU: ✅ 6 verified, 🟡 10 limited, 🔴 77 failed, ⚫ 0 blocked/skipped | GPU: ✅ 8, 🟡 0

Full matrix: [catalog/compatibility.md](catalog/compatibility.md)
<!-- generated:compatibility end -->

## Status summary

See [catalog/compatibility.md](catalog/compatibility.md) for the full generated matrix and [reports/marathon-progress.md](reports/marathon-progress.md) for live campaign progress.

## Quick start

```bash
uv venv .venv-cpu --python 3.12
uv pip install --python .venv-cpu/bin/python -e ".[dev]"
# + the notebook execution stack (see docs/getting-started.md)

python -m ov_amd doctor          # hardware/software/venv audit
python -m ov_amd list            # catalog + statuses
python -m ov_amd run hello-world --device cpu
python -m ov_amd compare hello-world
python scripts/run_marathon.py   # unattended, resumable campaign
```

## Status model (short version)

| Icon | Status |
|---|---|
| ✅ | VERIFIED — environment + model + inference + correctness OK, repeatable (≥3 runs for cheap workloads), evidence captured |
| 🟡 | VERIFIED_WITH_LIMITATIONS — succeeded under a documented modification/limitation (e.g. skipped UI-only cells, single repeatability run) |
| 🔴 | FAILED — executed and failed; category recorded |
| ⚫ | BLOCKED / SKIPPED_RESOURCE |
| ⏳ | NOT_TESTED |
| ➖ | NOT_APPLICABLE |

Full definitions: [docs/validation-policy.md](docs/validation-policy.md).

> **"Verified" means the workload was reproduced successfully on the hardware and software configuration documented by this project. It does not imply official hardware support or certification by the OpenVINO project, Intel, AMD, or the original model authors.**

## Repository layout

| Path | Content |
|---|---|
| `catalog/` | generated compatibility matrix (json + md) |
| `upstream/` | pinned upstream commit metadata |
| `workloads/<id>/` | workload manifests, ROCm twin scripts, validation config |
| `results/<id>/<ts>-<backend>/` | evidence directories (hardware/software/execution/metrics/logs) |
| `results/marathon-state.json` | resumable campaign checkpoint |
| `ov_amd/` | validation harness + CLI |
| `scripts/` | discovery / marathon / cache / revalidation entry points |
| `benchmarks/METHODOLOGY.md` | how numbers are measured |
| `reports/` | preflight, progress, failures, final report |

## License

Apache-2.0 — see [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md). OpenVINO Notebooks retains its own copyright and license; model and dataset licenses remain independent and are never overridden by this repository's license.
