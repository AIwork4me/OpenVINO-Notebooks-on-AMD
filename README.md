# OpenVINO Notebooks on AMD

[![CI](https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/ci.yml/badge.svg)](https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Validation Schema](https://img.shields.io/badge/evidence_schema-v2-informational)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

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
**AMD CPU Coverage: 171/171 OpenVINO Notebooks attempted on AMD Ryzen — 100.0% catalog coverage**

✅ 25 Verified · 🟡 60 Verified with limitations · 🚧 80 Blocked (network / model access / dependency / timeout / resource) · 🧩 5 Compatibility failures · ➖ 1 Not applicable

> **100% coverage means every catalogued notebook has been attempted and classified on AMD Ryzen. It does not mean every notebook passed.**

Successful executions: **85/170** of eligible notebooks (50.0%) — ✅ 25 L3 verified · 🟡 60 with documented limitations.

GPU (ROCm twins, Radeon): ✅ 8 verified · 🟡 0 limited

Evidence Schema **v2** · upstream `329562e6031d` · twin classification **171/171** (100.0%)

Full matrix: [catalog/compatibility.md](catalog/compatibility.md) · Methodology: [docs/validation-policy.md](docs/validation-policy.md) · [benchmarks/METHODOLOGY.md](benchmarks/METHODOLOGY.md)
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
