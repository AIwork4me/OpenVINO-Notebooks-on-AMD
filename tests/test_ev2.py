"""Evidence Schema v2: aggregates, device proof, status policy (defects E, F, G, H)."""

import json

from ov_amd import ev2
from ov_amd.schemas import Status

# ---------------------------------------------------------------------------
# repeatability aggregate (Defect G)
# ---------------------------------------------------------------------------


def test_aggregate_counts_and_median():
    agg = ev2.aggregate_repeatability([10.0, 12.0, 11.0], required_runs=3)
    assert agg["successful_runs"] == 3
    assert agg["required_runs"] == 3
    assert agg["repeatability_passed"] is True
    assert agg["median_latency_s"] == 11.0


def test_aggregate_p95_nearest_rank():
    values = list(range(1, 21))  # 1..20 -> p95 rank ceil(0.95*20)=19 -> value 19
    agg = ev2.aggregate_repeatability([float(v) for v in values], required_runs=3)
    assert agg["p95_latency_s"] == 19.0


def test_aggregate_single_run_is_not_repeatability_passed():
    agg = ev2.aggregate_repeatability([9.0], required_runs=3)
    assert agg["successful_runs"] == 1
    assert agg["repeatability_passed"] is False


def test_aggregate_failed_runs_are_not_hidden():
    """Failed attempts simply do not contribute durations; the aggregate must
    expose required vs successful so the gap is visible."""
    agg = ev2.aggregate_repeatability([5.0], required_runs=3)
    assert agg["successful_runs"] < agg["required_runs"]
    assert agg["repeatability_passed"] is False


# ---------------------------------------------------------------------------
# device proof (Defect E)
# ---------------------------------------------------------------------------


def _write_probe(tmp_path, events):
    p = tmp_path / "device-proof.jsonl"
    p.write_text("".join(json.dumps(e) + "\n" for e in events))
    return p


def test_probe_empty_is_unknown_not_cpu(tmp_path):
    proof = ev2.summarize_device_proof(tmp_path / "missing.jsonl", "cpu", "")
    assert ev2.proof_state(proof) is ev2.DeviceProof.UNKNOWN


def test_probe_execution_devices_cpu(tmp_path):
    p = _write_probe(tmp_path, [{"kind": "compile_model", "device_arg": "AUTO", "execution_devices": ["CPU"]}])
    proof = ev2.summarize_device_proof(p, "cpu", "")
    assert ev2.proof_state(proof) is ev2.DeviceProof.PROVEN_CPU


def test_probe_execution_devices_gpu_is_not_proven_cpu(tmp_path):
    p = _write_probe(tmp_path, [{"kind": "compile_model", "device_arg": "GPU", "execution_devices": ["GPU"]}])
    proof = ev2.summarize_device_proof(p, "cpu", "GPU")
    assert ev2.proof_state(proof) is ev2.DeviceProof.PROVEN_GPU


def test_probe_auto_unresolved(tmp_path):
    p = _write_probe(tmp_path, [{"kind": "compile_model", "device_arg": "AUTO", "execution_devices": None}])
    proof = ev2.summarize_device_proof(p, "cpu", "")
    assert ev2.proof_state(proof) is ev2.DeviceProof.AUTO_UNRESOLVED


def test_probe_no_compile_is_not_inference(tmp_path):
    p = _write_probe(tmp_path, [{"kind": "probe_installed"}])
    proof = ev2.summarize_device_proof(p, "cpu", "")
    assert ev2.proof_state(proof) is ev2.DeviceProof.NOT_INFERENCE


def test_widget_text_alone_never_proves(tmp_path):
    proof = ev2.summarize_device_proof(None, "cpu", "CPU")
    assert ev2.proof_state(proof) is ev2.DeviceProof.UNKNOWN


# ---------------------------------------------------------------------------
# status policy (Defects E + F)
# ---------------------------------------------------------------------------


def test_full_requirements_give_verified():
    status, notes, level = ev2.decide_status(
        runs_ok=3, required_runs=3, contract_present=True, proof=ev2.DeviceProof.PROVEN_CPU, n_cells=5, n_skipped=0
    )
    assert status == Status.VERIFIED.value
    assert level == ev2.ValidationLevel.WORKLOAD_CORRECTNESS


def test_gpu_execution_cannot_become_cpu_verified():
    status, notes, _ = ev2.decide_status(
        runs_ok=3, required_runs=3, contract_present=True, proof=ev2.DeviceProof.PROVEN_GPU, n_cells=5, n_skipped=0
    )
    assert status == Status.VERIFIED_WITH_LIMITATIONS.value
    assert any("GPU" in n for n in notes)


def test_auto_unresolved_cannot_become_verified():
    status, notes, _ = ev2.decide_status(
        runs_ok=3, required_runs=3, contract_present=True, proof=ev2.DeviceProof.AUTO_UNRESOLVED, n_cells=5, n_skipped=0
    )
    assert status == Status.VERIFIED_WITH_LIMITATIONS.value
    assert any("DEVICE_PROOF_INCOMPLETE" in n for n in notes)


def test_empty_device_cannot_become_verified():
    status, _, _ = ev2.decide_status(
        runs_ok=3, required_runs=3, contract_present=True, proof=ev2.DeviceProof.UNKNOWN, n_cells=5, n_skipped=0
    )
    assert status != Status.VERIFIED.value


def test_empty_validation_is_execution_only_never_verified():
    status, notes, level = ev2.decide_status(
        runs_ok=3, required_runs=3, contract_present=False, proof=ev2.DeviceProof.PROVEN_CPU, n_cells=5, n_skipped=0
    )
    assert status == Status.VERIFIED_WITH_LIMITATIONS.value
    assert level == ev2.ValidationLevel.EXECUTION_ONLY
    assert any("EXECUTION_ONLY" in n for n in notes)


def test_single_run_cannot_become_verified():
    status, notes, _ = ev2.decide_status(
        runs_ok=1, required_runs=1, contract_present=True, proof=ev2.DeviceProof.PROVEN_CPU, n_cells=5, n_skipped=0
    )
    assert status == Status.VERIFIED_WITH_LIMITATIONS.value
    assert any("repeatability_not_established" in n for n in notes)


def test_zero_cells_is_not_applicable():
    status, _, level = ev2.decide_status(
        runs_ok=1, required_runs=1, contract_present=False, proof=ev2.DeviceProof.UNKNOWN, n_cells=0, n_skipped=0
    )
    assert status == Status.NOT_APPLICABLE.value


# ---------------------------------------------------------------------------
# schema versioning
# ---------------------------------------------------------------------------


def test_write_json_stamps_schema_version(tmp_path):
    p = tmp_path / "x" / "metrics.json"
    ev2.write_json(p, {"a": 1})
    assert json.loads(p.read_text())["schema_version"] == 2
    assert ev2.evidence_schema_version(p) == 2


def test_v1_file_is_not_v2(tmp_path):
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps({"runs_ok": 0}))
    assert ev2.evidence_schema_version(p) is None


def test_genai_pipeline_device_arg_is_method_b_evidence(tmp_path):
    """openvino_genai pipelines compile internally; the explicit device
    argument is still positive proof (documented Method B extension)."""
    p = _write_probe(tmp_path, [
        {"kind": "probe_installed"},
        {"kind": "genai_pipeline", "pipeline": "LLMPipeline", "device_arg": "CPU"},
    ])
    proof = ev2.summarize_device_proof(p, "cpu", "")
    assert ev2.proof_state(proof) is ev2.DeviceProof.PROVEN_CPU
    assert proof["genai_pipeline_events"] == 1


def test_genai_gpu_device_arg_is_not_proven_cpu(tmp_path):
    p = _write_probe(tmp_path, [
        {"kind": "genai_pipeline", "pipeline": "LLMPipeline", "device_arg": "GPU"},
    ])
    proof = ev2.summarize_device_proof(p, "cpu", "")
    assert ev2.proof_state(proof) is ev2.DeviceProof.PROVEN_GPU
