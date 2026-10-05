# Upstream Update Impact (v0.2)

Generated: 2026-10-06 (queries via GitHub API; recorded before switching the pin).

## Commit delta

| | |
|---|---|
| Old pinned commit | `a8809170cc4fc6aa633fbb9c22214be67ac20b47` (2026-09-30, branch `latest`) |
| Current `latest` HEAD | `329562e6031d1a989017d08697b0fabe5a989492` (2026-10-05T16:50:18Z) |
| Commits between | 8 |
| Files changed | 61 |

## Commits

- `22060686` Bump eslint-plugin-react-hooks (selector only — no notebook impact)
- `f21d2de0` Bump react group (selector only)
- `4ce4c0ec` Bump setup_python CI action (CI only)
- `edf3aab4` **fix: pass optimum-cli args as a list to preserve paths with spaces** (`utils/cmd_helper.py`)
- `91e221e2` Configurable notebooks directory location option (CI helper)
- `80340424` Fix notebook CI failures in dependency setup and model export
- `31f19fad` **Disabling support of python 3.10** (`.binder/runtime.txt` → `python-3.11`; CI supports 3.11/3.12/3.13)
- `329562e6` **CI copies `notebook_utils.py` into notebook folders before tests** instead of runtime download

## Changed notebooks (13)

3D-point-pillars, cosyvoice3-tts, flex.2-image-generation, hunyuan-ocr,
kokoro, llm-rag-langchain, ltx-video, ministral-3, olmocr-pdf-vlm,
openvoice2-and-melotts, sam2-image-segmentation, sam2-video-segmentation,
smolvlm2.

No new or removed notebooks in this window.

## Impact on this project

1. **Python policy (STEP 22):** upstream dropped 3.10 and supports 3.11–3.13.
   This repository already validates on Python 3.12 — aligned; `requires-python`
   stays `>=3.10`-compatible code but the reference validation Python remains
   3.12 (recorded in evidence).
2. **`utils/cmd_helper.py` optimum-cli fix:** our pinned snapshot ships this
   helper to notebooks that call `optimum-cli`; after re-pin, path-with-spaces
   handling improves (several CPU failures in v0.1 were optimum-cli-related).
3. **`notebook_utils.py` distribution change:** upstream now copies the helper
   into each notebook folder at CI time; at runtime notebooks still fall back
   to `Path("notebook_utils.py").exists()` — our preseeded copy continues to
   satisfy this. After re-pin the snapshot may ship per-folder copies; the
   sibling-preseed path in `ov_amd/notebook_runner.py` already copies them.
4. **Changed notebooks must be revalidated after re-pin (STEP 23)** — they will
   be marked REVALIDATION_REQUIRED at sync time; everything else keeps its
   pinned-baseline evidence.

## Sync decision

Per "change one variable at a time", the pin switch happens only after the
v0.2 Full Marathon on the old pinned commit establishes the clean baseline
(reports/v0.2-pinned-baseline.md).
