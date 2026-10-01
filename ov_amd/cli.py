"""Command line interface: python -m ov_amd <command>."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ov_amd import __version__
from ov_amd.environment import REPO_ROOT, venv_exists, venv_python
from ov_amd.executor import load_upstream_meta, workload_config
from ov_amd.scheduler import load_catalog, load_state


def cmd_doctor(args: argparse.Namespace) -> int:
    from ov_amd import hardware
    from ov_amd.environment import disk_free_mb, ram_available_mb

    hw = hardware.collect_hardware()
    print(f"ov-amd {__version__}")
    print(f"CPU:       {hw['cpu']['model']} ({hw['cpu']['threads']} threads)")
    print(f"RAM:       {hw['ram_total_mb'] // 1024} GB total, {ram_available_mb() // 1024} GB available")
    print(f"Disk free: {disk_free_mb() // 1024} GB")
    print(f"GPU:       {json.dumps(hw['gpu'])}")
    for backend in ("cpu", "gpu"):
        exists = venv_exists(backend)
        print(f"venv[{backend}]: {'present' if exists else 'MISSING'} ({venv_python(backend)})")
        if exists:
            sw = hardware.collect_software(str(venv_python(backend)))
            print(f"  openvino: {sw['openvino']['version']} devices={sw['openvino']['devices']}")
            print(f"  torch:    {sw['torch_rocm']['torch']} hip={sw['torch_rocm']['hip']} "
                  f"cuda_available={sw['torch_rocm']['cuda_available']}")
    meta = load_upstream_meta()
    print(f"upstream:  {meta.get('repository', '?')} @ {meta.get('commit', '?')[:12]} ({meta.get('branch', '?')})")
    state = load_state()
    print(f"attempts:  {len(state.get('attempts', {}))} recorded in results/marathon-state.json")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    entries = load_catalog()
    state = load_state()
    if args.category:
        entries = [e for e in entries if e.category == args.category]
    for e in sorted(entries, key=lambda e: (e.priority, e.id)):
        rec = state.get("attempts", {}).get(e.id, {})
        cpu = (rec.get("cpu") or {}).get("status", "NOT_TESTED")
        gpu = (rec.get("gpu") or {}).get("status", "NOT_TESTED")
        print(f"p{e.priority}  cpu={cpu:<28} gpu={gpu:<28} {e.id}")
    print(f"total: {len(entries)}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    entries = [e for e in load_catalog() if e.id == args.workload]
    if not entries:
        print(f"unknown workload: {args.workload}", file=sys.stderr)
        return 1
    e = entries[0]
    state = load_state()
    print(json.dumps({"entry": e.to_dict(), "attempts": state.get("attempts", {}).get(e.id, {}),
                      "config": workload_config(e)}, indent=2, default=str))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from ov_amd.executor import run_workload_cpu
    from ov_amd.marathon import run_gpu_twin
    from ov_amd.scheduler import save_state

    entries = [e for e in load_catalog() if e.id == args.workload]
    if not entries:
        print(f"unknown workload: {args.workload}", file=sys.stderr)
        return 1
    e = entries[0]
    state = load_state()
    if args.device == "cpu":
        out = run_workload_cpu(e, state)
        print(json.dumps({"status": out.status.value, "failure": out.failure_category,
                          "durations_s": out.durations, "device_used": out.device_used,
                          "notes": out.notes, "evidence": str(out.evidence_dir)}, indent=2))
        return 0 if out.status.value in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS") else 2
    run_gpu_twin(e, state)
    save_state(state)
    print(json.dumps(state["attempts"].get(e.id, {}).get("gpu", {}), indent=2))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from ov_amd.benchmark import load_gpu_metrics, merge_cpu_metrics
    from ov_amd.reporting import build_compatibility

    compat = build_compatibility()
    row = next((r for r in compat["rows"] if r["id"] == args.workload), None)
    if row is None:
        print(f"unknown workload: {args.workload}", file=sys.stderr)
        return 1
    state = load_state()
    rec = state.get("attempts", {}).get(args.workload, {})
    cpu = merge_cpu_metrics(args.workload, (rec.get("cpu") or {}).get("durations_s", []),
                            (rec.get("cpu") or {}).get("device_used", ""))
    gpu = load_gpu_metrics(args.workload)
    print(json.dumps({"workload": args.workload, "cpu": cpu, "gpu": gpu,
                      "statuses": {"cpu": row["cpu_status"], "gpu": row["gpu_status"]}}, indent=2))
    return 0


def cmd_marathon(args: argparse.Namespace) -> int:
    from ov_amd.marathon import run_marathon

    summary = run_marathon(
        cpu_only=args.cpu_only,
        gpu_only=args.gpu_only,
        max_runtime_s=args.max_runtime,
        retry_failed=args.retry_failed,
        category=args.category,
        priority_max=args.priority,
    )
    print(json.dumps(summary, indent=2))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from ov_amd.reporting import write_compatibility, write_failures, write_progress

    compat = write_compatibility()
    write_progress()
    write_failures()
    print(json.dumps(compat["counts"], indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ov_amd", description="OpenVINO Notebooks on AMD — validation harness")
    p.add_argument("--version", action="version", version=f"ov_amd {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor").set_defaults(func=cmd_doctor)

    sp = sub.add_parser("list")
    sp.add_argument("--category")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("info")
    sp.add_argument("workload")
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("run")
    sp.add_argument("workload")
    sp.add_argument("--device", choices=["cpu", "gpu"], default="cpu")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("compare")
    sp.add_argument("workload")
    sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser("marathon")
    for opt, dest in (("--cpu-only", "cpu_only"), ("--gpu-only", "gpu_only"), ("--retry-failed", "retry_failed")):
        sp.add_argument(opt, dest=dest, action="store_true")
    sp.add_argument("--max-runtime", type=float, default=None)
    sp.add_argument("--priority", type=int, default=None)
    sp.add_argument("--category", default=None)
    sp.set_defaults(func=cmd_marathon)

    sub.add_parser("report").set_defaults(func=cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def repo_root() -> Path:
    return REPO_ROOT


def _git(*a: str) -> str:  # small helper reused by scripts
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout
