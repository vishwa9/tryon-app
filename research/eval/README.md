# Eval set

A **fixed** set of 20 real garments, so that every engine version is measured on the same inputs.
`garments_manifest.csv` lists what to shoot. The mix is deliberate:

| Difficulty | Count | Purpose |
|---|---|---|
| `simple` | 8 | Plain tees, shirts, kurtas, a polo. **The exit gate is measured on these** (front + 3/4 views) |
| `medium` | 6 | Logos, stripes, checks, prints, sleeveless. Shows where it starts to break |
| `hard` | 6 | All-over prints, embroidery, jackets, bottoms, one garment without a back photo |

Keep the `garment_id`s. If you substitute a garment, update `category`, `notes` and `include_arms`
(`yes` when the garment's sleeves are longer than the house model's t-shirt sleeves).

## How to photograph (this is also the seller guidance we'll ship)

- **Plain, evenly lit background** (white sheet, light wall, or a big sheet of paper), with no other objects in frame.
- **Lay flat or hang**, smooth out wrinkles, sleeves arranged naturally, buttons done up.
- **Whole garment in frame** with a margin on every side. A garment that touches the edge is rejected (`GARMENT_CUT_OFF`).
- **Daylight or white light, no flash**, and avoid strong shadows. The notebook corrects the white balance using the background.
- **Camera straight above / in front**, phone at ~1–1.5 m, at least 1500 px on the long side, in focus (`BLURRY` is rejected).
- **Front and back** photos for each garment (except `g20`, which deliberately has no back photo).
- Name the files as in the manifest: `g01_front.jpg`, `g01_back.jpg`, …

## Scores (written by notebook 02)

| Column | Meaning |
|---|---|
| `colour_dE` | CIEDE2000 distance between dominant colours of flat-lay and output garment (lower is better; < ~5 is hard to see) |
| `pattern_sim` | DINOv2 cosine similarity between flat-lay and output garment crop (higher is better) |
| `leak` | Change outside the mask (should be 0; anything else is a bug) |
| `total` | 0–1 combined score used to sort candidates (weights in `phase0_utils.DEFAULT_WEIGHTS`) |
| `pass`, `fail_reason` | Your judgement: `Y`/`N` + one of `phase0_utils.FAIL_REASONS` |
| `sec_per_img`, `peak_vram_gb` | Cost inputs for the cost model |

Automatic scores only **rank** candidates. The verdict always comes from human review.
