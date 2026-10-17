# Licence register

Every model, LoRA and auxiliary network the pipeline uses, per [ADR-0004](adr/0004-open-weight-model-and-licence-policy.md).
A model may be used in `packages/engine` (production) **only** if both its weights and its outputs are cleared
for commercial use. Research notebooks may use "research only" entries, but these must be replaced or cleared before code moves to production.

Always download from the publisher's official repository. Re-check licences when bumping versions.

| Model / library | Official source | Licence | Commercial use | Used in | Checked |
|---|---|---|---|---|---|
| FLUX.2 [klein] 4B | `black-forest-labs/FLUX.2-klein-4B` (Hugging Face) | Apache 2.0 | Yes | notebooks 01, 02 (generation, inpainting) | 2026-10-17: licence per model card and BFL announcements; **re-verify on the model card before first use** |
| DINOv2 small | `facebook/dinov2-small` | Apache 2.0 | Yes | notebook 02 (pattern similarity) | 2026-10-17: re-verify on model card |
| SegFormer B2 clothes | `mattmdjaga/segformer_b2_clothes` | Model card lists a permissive licence (confirm); trained on the ATR human-parsing dataset, whose terms may restrict commercial use | **Unverified: research only** | notebook 01 (clothing masks) | 2026-10-17: needs review of the dataset terms; candidates to replace it: SAM 2 (Apache 2.0) with box prompts, or a parser trained on permissively licensed data |
| diffusers 0.41.0 | `huggingface/diffusers` | Apache 2.0 | Yes | notebooks | 2026-10-17: checked from the source headers |
| transformers | `huggingface/transformers` | Apache 2.0 | Yes | notebooks | 2026-10-17 |

## Not used (and why)

| Model | Reason |
|---|---|
| FLUX.2 [dev], FLUX.2 [klein] 9B | Non-commercial licence for the weights |
| InsightFace face-recognition models (e.g. ArcFace "buffalo" packs) | Non-commercial research licence. Identity is judged manually in Phase 0 |

## How to add an entry

1. Read the licence on the official model card **and** check the training-data terms when the card mentions them.
2. Add a row with the date and what you checked.
3. If commercial use is unclear, mark it **Unverified: research only** and open an issue to resolve it.
