# research

Phase-0 notebooks that test whether the generation pipeline in
[03-generation-pipeline](../docs/architecture/03-generation-pipeline.md) is good enough
**before** building more of the app.

**Exit criterion:** at least 70% of *simple upper-body garments* (front + 3/4 views) pass the
[quality bar](../docs/architecture/00-overview.md#quality-bar-catalog-quality), counting the best candidate per garment × angle.

## Contents

| Path | What |
|---|---|
| `notebooks/01_house_model.ipynb` | Stage A: create one synthetic house model → 5-angle pose set → clothing masks |
| `notebooks/02_garment_swap_eval.ipynb` | Stage B: swap each eval garment onto each angle, auto-score, manual review, report + verdict |
| `phase0_utils.py` | Shared helpers (garment prep, masks, compositing, scoring, report). No torch, so it's unit-tested on CPU |
| `tests/` | `python -m pytest research/tests -q` |
| `eval/` | Eval-set manifest and photo guide; `eval/reports/` holds committed results (CSV + JSON, no images) |
| `requirements.txt` | Pinned deps (diffusers 0.41.0 is the first release with the FLUX.2 [klein] pipelines) |

## How to run (Kaggle, free T4)

1. **Hugging Face token:** huggingface.co → Settings → Access Tokens → *Read*.
2. **Kaggle notebook:** *Create → New Notebook → File → Import Notebook* → upload `notebooks/01_house_model.ipynb`.
   - Settings: **Accelerator: GPU T4**, **Internet: on**.
   - *Add-ons → Secrets*: `HF_TOKEN`. If this repo is private, also `GITHUB_TOKEN` (fine-grained, read-only, this repo only).
3. **Run 01** top to bottom. Pick the identity and one image per angle when asked (edit `CHOSEN_IDENTITY` / `CHOSEN_POSES`).
   Check the mask overlays. Then *Save Version* so its output can be attached to 02.
4. **Eval photos:** shoot the garments listed in `eval/garments_manifest.csv` (see [eval/README](eval/README.md)),
   then upload the photos **plus your copy of the manifest** as a *private* Kaggle Dataset.
5. **Run 02** with two inputs attached: the 01 output and the photo dataset. Folders are found automatically.
   Start with `ONLY_GARMENTS = ["g01", "g02"]` for a quick check, then run all.
6. **Review** with `show(gid, angle)` + `mark(...)`, then run the report cell. Commit the resulting
   `<date>_<engine>.csv/.json` to `eval/reports/`.

Colab works the same way (Runtime → T4 GPU; secrets under 🔑). Notebook 02 is resumable after a disconnect.

## What to expect

- Each step of the pipeline is cheap, but T4/P100 cards have no native bf16, so expect tens of seconds per image.
  Time and peak VRAM are recorded for every candidate, and those numbers feed the cost model in [07-nfr](../docs/architecture/07-nfr.md).
- Identity consistency is judged by eye in Phase 0. Common face-embedding models have non-commercial licences.
- The clothing parser used for masks is **research-only** until its licence is cleared (see the
  [licence register](../docs/architecture/licence-register.md)). It must be replaced or cleared before this code moves into `packages/engine`.

## Data hygiene

- Weights, generated images and photos never go in git (`research/outputs/`, `research/data/` are git-ignored).
- Keep the eval photos private. Use your own products or ones you have the right to use.
