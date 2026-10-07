# Current Upstream Delta (generated)

Generated: 2026-10-07 — comprehensive verification closure §35.

## Commit range

| | |
|---|---|
| Project pin (unchanged) | `329562e6031d1a989017d08697b0fabe5a989492` (2026-10-05T16:50:18Z) |
| Upstream `latest` now | `faf88d73c65671cf34b0813ae44ff28f852508d1` (2026-10-06T19:33:31Z) |
| Commits between | 9 |
| Files changed | 18 (3 modified notebooks + 2 new-notebook files + READMEs + CI/selector + 2 shared utils) |

## Decision

**The pin stays at `329562e`.** Dataset pin-coherence after this closure's full
audit: 168 rows fully coherent + 3 disclosed warnings (pre-repin evidence on
changed notebook content: `llm-rag-langchain`, `ltx-video`,
`segment-anything-2-video` — revalidation queued; see
reports/full-171-integrity-audit.md). Rows are NOT flipped to
REVALIDATION_REQUIRED while the validated pin is unchanged; instead the
re-pin scope is recorded here and will be applied when the project decides to
move the pin (change one variable at a time — same policy as the v0.2 re-pin).

## Changed notebooks (re-pin scope: REVALIDATION_REQUIRED when pin moves)

| Notebook | Current CPU state | Note |
|---|---|---|
| `llm-chatbot` | 🟡 VERIFIED_WITH_LIMITATIONS | upstream added MiniCPM5-2B + stop-token fixes |
| `llm-chatbot-generate-api` | 🟡 VERIFIED_WITH_LIMITATIONS | same family changes |
| `openvino-tokenizers` | 🧩 FAILED_COMPATIBILITY (RCA-002) | upstream switched to nightly builds — may change the RCA-002 verdict; revalidate first |

## New upstream notebooks (catalog candidates, not in pinned catalog)

- `notebooks/pyannote-audio/pyannote-audio.ipynb` (speaker diarization)
- `notebooks/pyannote-audio/pyannote-embedding.ipynb`

Adding them grows the catalog beyond 171; queued for the next catalog refresh
(v0.3), keeping 171/171 coverage claims tied to the pinned catalog.

## Shared-helper change relevant to the failure dataset

`utils/notebook_utils.py` — commit `f1958fc8` *"Fix download_file() reusing a
corrupted file after an interrupted download"* — addresses exactly the
artifact-corruption mechanism hypothesized in
reports/upstream/rca-004-empty-weights-cluster.md. Recommended: pull this fix
into the snapshot at re-pin time and retry the RCA-004 cluster before any
further classification changes.
