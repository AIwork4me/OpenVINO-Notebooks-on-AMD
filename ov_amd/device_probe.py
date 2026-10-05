"""Kernel-side OpenVINO device probe (Evidence Schema v2, device proof).

This module is copied into each per-workload validation venv and wired via a
`.pth` file, so it activates in every kernel process of that venv without any
notebook modification. It is transparent instrumentation:

- If the environment variable OV_AMD_DEVICE_PROBE_FILE is set, every
  `Core.compile_model(...)` call is recorded (device argument and, when
  queryable, the runtime's own EXECUTION_DEVICES property) as one JSON line.
- Nothing else changes: the original call always executes; any probe error is
  swallowed after recording a note, so validation runs are never broken by the
  probe.

Proof policy (ov_amd/ev2.py): CPU VERIFIED requires a positive record of CPU
execution — the notebook's own runtime telling us where the model ran
(EXECUTION_DEVICES), or the explicit device argument when the runtime property
is unavailable. Widget selections ("device used: CPU" text) are supporting
evidence only and never sufficient alone.
"""

from __future__ import annotations

import json
import os
import sys
import time

PROBE_ENV = "OV_AMD_DEVICE_PROBE_FILE"
_MARKER = "openvino"


def _record(event: dict) -> None:
    path = os.environ.get(PROBE_ENV, "")
    if not path:
        return
    event = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}
    try:
        with open(path, "a") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except OSError:
        pass


def _patch_openvino(ov_module) -> None:
    try:
        core_cls = ov_module.runtime.Core
    except AttributeError:
        try:
            core_cls = ov_module.Core  # older flat API
        except AttributeError:
            return
    if getattr(core_cls, "_amd_probe_patched", False):
        return

    orig_compile = core_cls.compile_model

    def compile_model(self, *args, **kwargs):  # noqa: ANN002, ANN003 - mirrors stdlib signature
        device = kwargs.get("device_name")
        if device is None and len(args) >= 2 and isinstance(args[1], str):
            device = args[1]
        if device is None and len(args) == 1 and isinstance(args[0], str):
            # compile_model(model_xml_string) - no device argument form
            device = None
        try:
            compiled = orig_compile(self, *args, **kwargs)
        except Exception:
            _record({"kind": "compile_model_error", "device_arg": str(device)})
            raise
        exec_dev = None
        try:
            exec_dev = [str(d) for d in compiled.get_property("EXECUTION_DEVICES")]
        except Exception:
            exec_dev = None
        _record(
            {
                "kind": "compile_model",
                "device_arg": str(device) if device is not None else None,
                "execution_devices": exec_dev,
                "openvino_version": getattr(ov_module, "__version__", None),
            }
        )
        return compiled

    core_cls.compile_model = compile_model  # type: ignore[assignment]
    core_cls._amd_probe_patched = True  # type: ignore[attr-defined]
    _record({"kind": "probe_installed", "openvino_version": getattr(ov_module, "__version__", None)})


class _OpenvinoWatchFinder:
    """Meta-path finder: patch openvino right after its first import."""

    def find_spec(self, fullname, path=None, target=None):  # noqa: ANN001
        if fullname != _MARKER:
            return None
        try:
            sys.meta_path.remove(self)
        except ValueError:
            pass
        import importlib.util

        spec = importlib.util.find_spec(fullname)
        if spec is None or spec.loader is None:
            return None
        orig_loader = spec.loader

        class _Wrapper:
            def create_module(self, spec):  # noqa: ANN001
                return orig_loader.create_module(spec)

            def exec_module(self, module):  # noqa: ANN001
                orig_loader.exec_module(module)
                try:
                    _patch_openvino(module)
                except Exception as e:  # probe must never break the notebook
                    _record({"kind": "probe_install_error", "error": repr(e)})

        spec.loader = _Wrapper()  # type: ignore[assignment]
        return spec


class _GenaiWatchFinder:
    """Meta-path finder: patch openvino_genai pipeline constructors right
    after its first import (they compile models internally in C++, so the
    Python Core.compile_model hook never sees their device argument)."""

    def find_spec(self, fullname, path=None, target=None):  # noqa: ANN001
        # notebooks import either the top-level package or the submodule alias
        if fullname not in ("openvino_genai", "openvino.genai"):
            return None
        try:
            sys.meta_path.remove(self)
        except ValueError:
            pass
        import importlib.util

        spec = importlib.util.find_spec(fullname)
        if spec is None or spec.loader is None:
            return None
        orig_loader = spec.loader

        class _Wrapper:
            def create_module(self, spec):  # noqa: ANN001
                return orig_loader.create_module(spec)

            def exec_module(self, module):  # noqa: ANN001
                orig_loader.exec_module(module)
                try:
                    _patch_genai(module)
                except Exception as e:
                    _record({"kind": "probe_install_error", "error": repr(e)})

        spec.loader = _Wrapper()  # type: ignore[assignment]
        return spec


def _extract_device(args, kwargs):  # noqa: ANN001
    if isinstance(kwargs.get("device"), str):
        return kwargs["device"]
    if isinstance(kwargs.get("device_name"), str):
        return kwargs["device_name"]
    # pipelines: (models_path, device, ...) | (model_string, device, ...)
    if len(args) >= 2 and isinstance(args[1], str):
        return args[1]
    return None


def _patch_genai(genai_module) -> None:
    for name in dir(genai_module):
        if not name.endswith("Pipeline"):
            continue
        cls = getattr(genai_module, name)
        if not isinstance(cls, type) or getattr(cls, "_amd_probe_patched", False):
            continue
        orig_init = cls.__init__

        def make_patched(orig, pipeline_name):  # noqa: ANN001
            def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
                try:
                    _record({
                        "kind": "genai_pipeline",
                        "pipeline": pipeline_name,
                        "device_arg": _extract_device(args, kwargs),
                    })
                except Exception:
                    pass
                return orig(self, *args, **kwargs)

            return __init__

        try:
            cls.__init__ = make_patched(orig_init, name)  # type: ignore[method-assign]
            cls._amd_probe_patched = True  # type: ignore[attr-defined]
        except (TypeError, AttributeError):
            continue


def install() -> None:
    if not any(isinstance(f, _OpenvinoWatchFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _OpenvinoWatchFinder())
    if not any(isinstance(f, _GenaiWatchFinder) for f in sys.meta_path):
        sys.meta_path.append(_GenaiWatchFinder())


install()
