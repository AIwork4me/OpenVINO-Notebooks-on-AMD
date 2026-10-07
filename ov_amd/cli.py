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
    from ov_amd.scheduler import load_catalog

    hw = hardware.collect_hardware()
    print(f"ov-amd {__version__}")
    print(f"CPU:       {hw['cpu']['model']} ({hw['cpu']['threads']} threads)")
    print(f"RAM:       {hw['ram_total_mb'] // 1024} GB total, {ram_available_mb() // 1024} GB available")
    print(f"Disk free: {disk_free_mb() // 1024} GB")
    print(f"GPU:       {json.dumps(hw['gpu'])}")
    amd_cpu = "AMD" in str(hw["cpu"].get("model", ""))
    print(f"AMD CPU:   {'detected' if amd_cpu else 'NOT DETECTED (CPU validation premise not met)'}")
    for backend in ("cpu", "gpu"):
        exists = venv_exists(backend)
        print(f"venv[{backend}]: {'present' if exists else 'MISSING'} ({venv_python(backend)})")
        if exists:
            sw = hardware.collect_software(str(venv_python(backend)))
            print(f"  openvino: {sw['openvino']['version']} devices={sw['openvino']['devices']}")
            print(
                f"  torch:    {sw['torch_rocm']['torch']} hip={sw['torch_rocm']['hip']} "
                f"cuda_available={sw['torch_rocm']['cuda_available']}"
            )
    gpu_hw = hw.get("gpu") or {}
    rocm = bool(gpu_hw.get("available")) if isinstance(gpu_hw, dict) else False
    print(f"ROCm:      {'detected' if rocm else 'not detected (CPU validation works without it)'}")
    meta = load_upstream_meta()
    print(f"upstream:  {meta.get('repository', '?')} @ {meta.get('commit', '?')[:12]} ({meta.get('branch', '?')})")
    catalog = load_catalog()
    state = load_state()
    attempts = state.get("attempts", {})
    cpu_terminal = sum(1 for w in attempts.values() if (w.get("cpu") or {}).get("status"))
    print(
        f"catalog:   {len(catalog)} notebooks pinned; {cpu_terminal} CPU attempt records "
        "in results/marathon-state.json"
    )
    print(f"coverage:  {cpu_terminal}/{len(catalog)} CPU outcomes recorded "
          f"({round(100 * cpu_terminal / max(1, len(catalog)), 1)}%)")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    entries = load_catalog()
    state = load_state()
    if args.category:
        entries = [e for e in entries if e.category == args.category]
    if args.status:
        wanted = args.status.upper()
        entries = [
            e
            for e in entries
            if wanted in (
                (state.get("attempts", {}).get(e.id, {}).get("cpu") or {}).get("status", "NOT_TESTED"),
                (state.get("attempts", {}).get(e.id, {}).get("cpu") or {}).get("compatibility_outcome", ""),
                (state.get("attempts", {}).get(e.id, {}).get("gpu") or {}).get("status", "NOT_TESTED"),
            )
        ]
    for e in sorted(entries, key=lambda e: (e.priority, e.id)):
        rec = state.get("attempts", {}).get(e.id, {})
        cpu = (rec.get("cpu") or {}).get("status", "NOT_TESTED")
        outcome = (rec.get("cpu") or {}).get("compatibility_outcome", "")
        gpu = (rec.get("gpu") or {}).get("status", "NOT_TESTED")
        print(f"p{e.priority}  cpu={cpu:<28} outcome={outcome:<28} gpu={gpu:<12} {e.id}")
    total = len(load_catalog())
    attempts = state.get("attempts", {})
    outcomes: dict[str, int] = {}
    for w in attempts.values():
        c = w.get("cpu") or {}
        if c.get("compatibility_outcome"):
            outcomes[c["compatibility_outcome"]] = outcomes.get(c["compatibility_outcome"], 0) + 1
    print(f"\n{total} workloads")
    print(f"AMD CPU: {sum(outcomes.values())}/{total} classified")
    for k in (
        "VERIFIED",
        "VERIFIED_WITH_LIMITATIONS",
        "BLOCKED_NETWORK",
        "BLOCKED_MODEL_ACCESS",
        "BLOCKED_DEPENDENCY",
        "BLOCKED_TIMEOUT",
        "BLOCKED_RESOURCE",
        "FAILED_COMPATIBILITY",
        "NOT_APPLICABLE",
    ):
        if outcomes.get(k):
            print(f"  {k:<28} {outcomes[k]}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    entries = [e for e in load_catalog() if e.id == args.workload]
    if not entries:
        print(f"unknown workload: {args.workload}", file=sys.stderr)
        return 1
    e = entries[0]
    state = load_state()
    print(
        json.dumps(
            {"entry": e.to_dict(), "attempts": state.get("attempts", {}).get(e.id, {}), "config": workload_config(e)},
            indent=2,
            default=str,
        )
    )
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
        print(
            json.dumps(
                {
                    "status": out.status.value,
                    "failure": out.failure_category,
                    "durations_s": out.durations,
                    "device_used": out.device_used,
                    "notes": out.notes,
                    "evidence": str(out.evidence_dir),
                },
                indent=2,
            )
        )
        return 0 if out.status.value in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS") else 2
    run_gpu_twin(e, state)
    save_state(state)
    print(json.dumps(state["attempts"].get(e.id, {}).get("gpu", {}), indent=2))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from ov_amd.benchmark import comparison_policy, load_gpu_metrics, merge_cpu_metrics
    from ov_amd.reporting import build_compatibility

    compat = build_compatibility()
    row = next((r for r in compat["rows"] if r["id"] == args.workload), None)
    if row is None:
        print(f"unknown workload: {args.workload}", file=sys.stderr)
        return 1
    state = load_state()
    rec = state.get("attempts", {}).get(args.workload, {})
    cpu = merge_cpu_metrics(
        args.workload, (rec.get("cpu") or {}).get("durations_s", []), (rec.get("cpu") or {}).get("device_used", "")
    )
    gpu = load_gpu_metrics(args.workload)
    policy = comparison_policy(row["twin_level"])
    out = {
        "workload": args.workload,
        "twin_level": row["twin_level"],
        "comparison_policy": policy,
        "cpu": cpu,
        "gpu": gpu,
        "statuses": {"cpu": row["cpu_status"], "gpu": row["gpu_status"]},
    }
    if not policy["speedup_allowed"]:
        out["speedup"] = None
        out["speedup_note"] = (
            f"not an EXACT_TWIN ({row['twin_level']}): direct speedup claims are not valid — {policy['requirement']}"
        )
    print(json.dumps(out, indent=2))
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
    from ov_amd.manifest_sync import sync_manifests
    from ov_amd.reporting import write_compatibility, write_failures, write_progress

    sync_manifests()
    compat = write_compatibility()
    write_progress()
    write_failures()
    print(json.dumps(compat["counts"], indent=2))
    return 0


def cmd_env(args: argparse.Namespace) -> int:
    from ov_amd import env_manager

    entries = [e for e in load_catalog() if e.id == args.workload]
    if not entries:
        print(f"unknown workload: {args.workload}", file=sys.stderr)
        return 1
    if args.action == "info":
        print(json.dumps(env_manager.inspect_env(entries[0], backend=args.device), indent=2, default=str))
        return 0
    if args.action == "rebuild":
        from ov_amd.environment import upstream_root

        root = upstream_root()
        nb_path = (root / entries[0].upstream_path) if root else None
        if nb_path is None or not nb_path.exists():
            print(json.dumps({"rebuilt": False, "error": "notebook not in upstream snapshot"}))
            return 2
        try:
            # identity: a rebuild must produce EXACTLY what the marathon path
            # would — same fingerprint inputs (incl. workload extra_deps) and
            # same notebook-requirements install (gate finding: same key must
            # mean same content)
            from ov_amd.executor import workload_config

            cfg = workload_config(entries[0])
            extra = list((cfg.get("env") or {}).get("extra_deps") or [])
            fp = env_manager.dependency_fingerprint(nb_path, extra_deps=extra)
            commit = json.loads((REPO_ROOT / "upstream" / "openvino-notebooks.json").read_text()).get("commit", "")
            info = env_manager.build_env(
                args.device, fp, upstream_commit=commit, extra_deps=extra,
                requirements=env_manager._requirements_next_to(nb_path),
            )
            print(json.dumps({"rebuilt": True, "env_key": info.env_key, "fingerprint": info.fingerprint}, indent=2))
            return 0
        except RuntimeError as e:
            print(json.dumps({"rebuilt": False, "error": str(e)[:1000]}, indent=2))
            return 2
    print(f"unknown env action: {args.action}", file=sys.stderr)
    return 1


def cmd_env_gc(args: argparse.Namespace) -> int:
    from ov_amd import env_manager

    removed = env_manager.gc_envs(backend=args.device, dry_run=not args.apply)
    print(
        json.dumps(
            {"mode": "dry-run (pass --apply to delete)" if not args.apply else "applied", "candidates": removed},
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ov_amd", description="OpenVINO Notebooks on AMD — validation harness")
    p.add_argument("--version", action="version", version=f"ov_amd {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor").set_defaults(func=cmd_doctor)

    sp = sub.add_parser("list")
    sp.add_argument("--category")
    sp.add_argument("--status", help="filter by execution status or compatibility outcome (verified, blocked, FAILED_COMPATIBILITY, ...)")
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

    sp = sub.add_parser("env")
    sp.add_argument("action", choices=["info", "rebuild"])
    sp.add_argument("workload")
    sp.add_argument("--device", choices=["cpu", "gpu"], default="cpu")
    sp.set_defaults(func=cmd_env)

    sp = sub.add_parser("env-gc")
    sp.add_argument("--device", choices=["cpu", "gpu"], default=None)
    sp.add_argument("--apply", action="store_true", help="actually delete (default: dry run)")
    sp.set_defaults(func=cmd_env_gc)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def repo_root() -> Path:
    return REPO_ROOT


def _git(*a: str) -> str:  # small helper reused by scripts
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout
