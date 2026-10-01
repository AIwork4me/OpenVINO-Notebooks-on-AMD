"""Standalone notebook executor run inside the validation venv.

Usage:
  python _nbexec.py <notebook.ipynb> <out.ipynb> <per_cell_timeout>
      [--skip-re RE]... [--stop-after-re RE] [--sub PAT:REP]...

Cell patching (all recorded in the result JSON):
  --skip-re RE       cells whose source matches RE are skipped (kept as raw, tagged)
  --stop-after RE    execution stops after the first cell matching RE
  --sub PAT:REP      regex substitution PAT -> REP applied to every cell source
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback

import nbformat
from nbclient import NotebookClient


def cell_source(cell) -> str:
    try:
        return cell.source or ""
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("notebook")
    ap.add_argument("out_notebook")
    ap.add_argument("per_cell_timeout", type=int)
    ap.add_argument("--skip-re", action="append", default=[])
    ap.add_argument("--stop-after-re", default=None)
    ap.add_argument("--sub", action="append", default=[])
    args = ap.parse_args()

    t0 = time.time()
    result = {
        "ok": False,
        "n_cells": 0,
        "n_skipped": 0,
        "n_substituted": 0,
        "stopped_after": None,
        "error_cell": None,
        "error_type": None,
        "error_head": None,
        "duration_s": 0.0,
        "patch_notes": [],
    }

    nb = nbformat.read(args.notebook, as_version=4)
    cells = [c for c in nb.cells if c.cell_type == "code"]
    result["n_cells"] = len(cells)

    skip_res = [re.compile(p) for p in args.skip_re]
    stop_re = re.compile(args.stop_after_re) if args.stop_after_re else None
    subs = []
    for s in args.sub:
        pat, _, rep = s.partition(":")
        subs.append((re.compile(pat), rep, s))

    exec_idx = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        src = cell_source(cell)
        if any(r.search(src) for r in skip_res):
            cell.cell_type = "raw"
            cell.get("metadata", {})["amd_skip_reason"] = "matched skip-re"
            result["n_skipped"] += 1
            result["patch_notes"].append(f"skipped cell {i}: matched skip pattern")
            continue
        if subs:
            new_src = src
            n_subs = 0
            for pat, rep, _ in subs:
                new_src, n = pat.subn(rep, new_src)
                n_subs += n
            if n_subs:
                cell.source = new_src
                result["n_substituted"] += 1
                result["patch_notes"].append(f"substituted {n_subs} occurrence(s) in cell {i}")
        exec_idx.append(i)
        if stop_re and stop_re.search(cell_source(cell)):
            result["stopped_after"] = i
            result["patch_notes"].append(f"stopped after cell {i} (matched stop pattern)")
            break

    try:
        if result["stopped_after"] is not None:
            # drop code cells after stop index so they are not executed
            kept = []
            for i, cell in enumerate(nb.cells):
                if i > result["stopped_after"] and cell.cell_type == "code":
                    cell.cell_type = "raw"
                    cell.get("metadata", {})["amd_skip_reason"] = "after stop pattern"
                kept.append(cell)
            nb.cells = kept
        t_start = time.time()

        def _on_start(cell, cell_index):
            src = cell_source(cell)[:70].replace("\n", " | ")
            print(f"[cell {cell_index} START +{time.time() - t_start:7.1f}s] {src}", flush=True)

        def _on_done(cell, cell_index, execute_reply=None):
            print(f"[cell {cell_index} DONE  +{time.time() - t_start:7.1f}s]", flush=True)

        client = NotebookClient(
            nb,
            timeout=args.per_cell_timeout,
            kernel_name="python3",
            allow_errors=False,
            on_cell_start=_on_start,
            on_cell_executed=_on_done,
        )
        client.execute()
        result["ok"] = True
    except Exception as e:  # noqa: BLE001 - record whatever the kernel raised
        tb = traceback.format_exc()
        result["error_type"] = type(e).__name__
        result["error_head"] = tb.strip().splitlines()[-1][:500] if tb else str(e)[:500]
        sys.stderr.write(tb[-8000:])
    finally:
        result["duration_s"] = round(time.time() - t0, 2)
        nbformat.write(nb, args.out_notebook)

    print("NBEXEC_RESULT=" + json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
