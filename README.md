# OpenVINO Notebooks on AMD

[![CI](https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/ci.yml/badge.svg)](https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Validation Schema](https://img.shields.io/badge/evidence_schema-v2-informational)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

> **Validate and run OpenVINO Notebooks on AMD Ryzen CPUs, with matching ROCm-powered references for AMD Radeon GPUs.**

> **One AI workload. Two AMD paths.**

This is **an AMD validation and ROCm companion project for [OpenVINO Notebooks](https://github.com/openvinotoolkit/openvino_notebooks)** — not a fork. Upstream notebooks are executed unmodified (or with documented, minimal patches) at a pinned upstream commit, on real AMD hardware, with machine-generated evidence for every claim.

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

## AMD CPU Coverage: 100%

<!-- generated:compatibility begin -->
**AMD CPU Coverage: 171/171 OpenVINO Notebooks attempted on AMD Ryzen — 100.0% catalog coverage**

✅ 25 Verified · 🟡 60 Verified with limitations · 🚧 80 Blocked (network / model access / dependency / timeout / resource) · 🧩 5 Compatibility failures · ➖ 1 Not applicable

> **100% coverage means every catalogued notebook has been attempted and classified on AMD Ryzen. It does not mean every notebook passed.**

Successful executions: **85/170** of eligible notebooks (50.0%) — ✅ 25 L3 verified · 🟡 60 with documented limitations.

GPU (ROCm twins, Radeon): ✅ 8 verified · 🟡 0 limited

Evidence Schema **v2** · upstream `329562e6031d` · twin classification **171/171** (100.0%)

Full matrix: [catalog/compatibility.md](catalog/compatibility.md) · Methodology: [docs/validation-policy.md](docs/validation-policy.md) · [benchmarks/METHODOLOGY.md](benchmarks/METHODOLOGY.md)
<!-- generated:compatibility end -->

### What "100% coverage" means — and what it does not

```text
100% catalog coverage  ≠  100% pass rate
```

- **Coverage** — every OpenVINO Notebook in the pinned catalog has a recorded AMD CPU validation outcome (evidence directory, device proof, classification).
- **Verified** — inference ran on AMD Ryzen with positive CPU device proof and workload-correctness evidence, repeatable per policy.
- **Verified with limitations** — ran successfully under a documented limitation (single repeatability run, skipped UI-only cells, execution-only without a correctness contract).
- **Blocked** — could not complete for an external/environment reason: gated model, unreachable host, missing dependency/CLI, timeout during download/conversion, insufficient resource. **Blocked is not an AMD/OpenVINO compatibility verdict.**
- **Compatibility failure** — the environment was valid, but the workload exposed a real runtime/model issue (e.g. an OpenVINO CPU-plugin rejection); each carries a root-cause record.

The distinction is strict everywhere: matrix, reports, release notes, and this README. Coverage is complete; evidence is auditable; failures are classified honestly.

## Compatibility matrix

- Full generated matrix (171 rows, outcome + validation level + reason + evidence link): [catalog/compatibility.md](catalog/compatibility.md)
- Live campaign progress: [reports/marathon-progress.md](reports/marathon-progress.md)
- Failure groups by outcome: [reports/failures.md](reports/failures.md)
- Full dataset audit: [reports/full-171-integrity-audit.md](reports/full-171-integrity-audit.md)

## Quick start

```bash
git clone https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD.git
cd OpenVINO-Notebooks-on-AMD

uv venv .venv-cpu --python 3.12
uv pip install --python .venv-cpu/bin/python -e ".[dev]"
# + the notebook execution stack (see docs/getting-started.md)

python -m ov_amd doctor          # hardware/software/venv audit
python -m ov_amd list            # catalog + statuses + coverage summary
python -m ov_amd info hello-world
python -m ov_amd run hello-world --device cpu
python -m ov_amd compare hello-world
python scripts/run_marathon.py   # unattended, resumable campaign
```

## Status model (two dimensions)

The runner records what it observed; developers read what it means.

| Execution status (internal) | Compatibility outcome (developer-facing) | Icon |
|---|---|---|
| VERIFIED | VERIFIED | ✅ |
| VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | 🟡 |
| FAILED ← network/host | BLOCKED_NETWORK | 🌐 |
| FAILED ← gated/restricted model | BLOCKED_MODEL_ACCESS | 🔐 |
| FAILED ← missing package/CLI/drift | BLOCKED_DEPENDENCY | 📦 |
| FAILED ← wall/cell timeout | BLOCKED_TIMEOUT (stage-aware) | ⏱️ |
| FAILED/OOM/disk/artifact | BLOCKED_RESOURCE | 💾 |
| FAILED ← runtime/model execution | FAILED_COMPATIBILITY | 🧩 |
| NOT_APPLICABLE | NOT_APPLICABLE | ➖ |

Full definitions: [docs/validation-policy.md](docs/validation-policy.md).

> **"Verified" means the workload was reproduced successfully on the hardware and software configuration documented by this project. It does not imply official hardware support or certification by the OpenVINO project, Intel, AMD, or the original model authors.**

## Methodology & evidence

Every row in the matrix is machine-generated from a resumable campaign checkpoint (`results/marathon-state.json`) — nothing is hand-entered. Each attempt produces an evidence directory (`results/<workload>/<ts>-<backend>/`) with hardware/software snapshots, upstream pin + notebook sha, device-proof probe events, repeatability aggregates, and validation contracts (Evidence Schema v2). Validation levels: L1 EXECUTION_ONLY → L3 WORKLOAD_CORRECTNESS; green requires L3 + positive `PROVEN_CPU` device proof + repeatability. See [docs/validation-policy.md](docs/validation-policy.md) and [benchmarks/METHODOLOGY.md](benchmarks/METHODOLOGY.md) (WORKLOAD_TWIN rows never carry CPU-vs-GPU speedup claims).

## Repository layout

| Path | Content |
|---|---|
| `catalog/` | generated compatibility matrix (json + md) |
| `upstream/` | pinned upstream commit metadata |
| `workloads/<id>/` | workload manifests, ROCm twin scripts, validation config |
| `results/<id>/<ts>-<backend>/` | evidence directories (hardware/software/execution/metrics/logs) |
| `results/marathon-state.json` | resumable campaign checkpoint (source of truth) |
| `ov_amd/` | validation harness + CLI |
| `scripts/` | discovery / marathon / cache / revalidation / audit entry points |
| `benchmarks/METHODOLOGY.md` | how numbers are measured |
| `reports/` | preflight, progress, failures, audits, final reports |
| `reports/upstream/` | root-cause analyses for genuine compatibility issues |

## Contributing & more hardware

Contributions welcome: new AMD CPU results (attach Evidence Schema v2 output), new AMD hardware reports, ROCm twins, failure reproductions, and upstream issue candidates. See [CONTRIBUTING.md](CONTRIBUTING.md). Every claimed result requires its evidence directory — no evidence, no row.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md). OpenVINO Notebooks retains its own copyright and license; model and dataset licenses remain independent and are never overridden by this repository's license.
