# Adding a Workload

Workload directories are generated automatically on first attempt
(`workloads/<id>/workload.yaml`), but you can pre-configure behavior:

```yaml
id: hello-world
title: Hello World
category: API
upstream:
  repository: openvinotoolkit/openvino_notebooks
  branch: latest
  commit: <pinned>
  path: notebooks/hello-world/hello-world.ipynb
  url: https://github.com/...
model:
  name: ...
  source: ...
  revision: ...
  license: ...
cpu:
  runtime: openvino
  status: NOT_TESTED
  wall_timeout_s: 1200        # optional override
  repeats: 3                  # optional override
gpu:
  runtime: pytorch-rocm
  status: NOT_TESTED
twin:
  level: WORKLOAD_TWIN
validation:                    # evaluated against executed outputs
  output_contains:
    - "some expected text"
  output_not_contains:
    - "nan"
  output_finite_numbers: true
  min_output_chars: 50
patches:                       # documented cell patches (D4)
  skip_cells_matching:
    - "gradio"
    - "demo\\.launch"
  stop_after_cell_matching: null
  cell_subs:                   # PAT:REP applied to every cell
    - "device\\s*=\\s*['\"]AUTO['\"] :device = 'CPU'"
```

## Adding a ROCm twin

Create `workloads/<id>/rocm/run.py`. Contract:

```python
# arg: --evidence-dir <dir>
# must print on success:
# TWIN_RESULT={"ok": true, "hip": torch.version.hip, "metrics": {...}}
```

- assert `torch.version.hip is not None` and a real AMD GPU is visible
- write metrics.json into the evidence dir
- reuse official model APIs (model repo / transformers / diffusers / torchvision)
- keep core logic in the script so notebooks can call the same implementation

Then: `python -m ov_amd run <id> --device gpu`.
