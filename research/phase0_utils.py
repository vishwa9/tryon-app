"""Helpers for the Phase-0 quality notebooks.

Pure numpy / scikit-image / Pillow: nothing here imports torch or downloads models,
so it can be unit-tested on a CPU (see research/tests/). Functions that prove
themselves here are meant to move into packages/engine later.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from skimage import color, filters, measure, morphology
from scipy import ndimage

# --------------------------------------------------------------------------- #
# Angles and which garment photo each one uses (docs/architecture/03)
# --------------------------------------------------------------------------- #

ANGLES = ["front", "three_quarter_left", "three_quarter_right", "side", "back"]

ANGLE_PHRASES = {
    "front": "facing the camera directly, front view",
    "three_quarter_left": "body turned 45 degrees to his left, three-quarter view, face towards camera",
    "three_quarter_right": "body turned 45 degrees to his right, three-quarter view, face towards camera",
    "side": "standing in full profile, side view facing left",
    "back": "seen from behind, back view, back of the head visible, face not visible",
}

# Angles that count towards the Phase-0 exit criterion.
EXIT_ANGLES = {"front", "three_quarter_left", "three_quarter_right"}
EXIT_THRESHOLD = 0.70

FAIL_REASONS = [
    "COLOUR_MISMATCH",
    "PRINT_OR_LOGO_WRONG",
    "SHAPE_WRONG",       # neckline, sleeve length, hem, buttons, pockets
    "ARTEFACT_HANDS",
    "ARTEFACT_EDGES",    # collar/mask seams, halo
    "IDENTITY_DRIFT",
    "NOT_STUDIO_LOOK",
    "OTHER",
]


def garment_ref_for_angle(angle: str, has_back: bool) -> tuple[str | None, str | None]:
    """Return (which flat-lay to use, skip_reason). The back is never inferred."""
    if angle not in ANGLES:
        raise ValueError(f"unknown angle {angle!r}")
    if angle == "back":
        return ("back", None) if has_back else (None, "NO_BACK_PHOTO")
    return "front", None


# --------------------------------------------------------------------------- #
# Runtime helpers
# --------------------------------------------------------------------------- #

def detect_runtime() -> str:
    if os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
        return "kaggle"
    try:
        import google.colab  # noqa: F401
        return "colab"
    except ImportError:
        return "local"


def get_secret(name: str) -> str | None:
    """Read a secret from Kaggle Secrets, Colab userdata, or the environment."""
    runtime = detect_runtime()
    try:
        if runtime == "kaggle":
            from kaggle_secrets import UserSecretsClient
            return UserSecretsClient().get_secret(name)
        if runtime == "colab":
            from google.colab import userdata
            return userdata.get(name)
    except Exception:
        pass
    return os.environ.get(name)


@contextmanager
def timer(store: dict, key: str):
    t0 = time.perf_counter()
    yield
    store[key] = round(time.perf_counter() - t0, 2)


# --------------------------------------------------------------------------- #
# Image basics
# --------------------------------------------------------------------------- #

def load_rgb(path: str | Path) -> Image.Image:
    """Open an image, apply its EXIF rotation (phone photos), return RGB without EXIF."""
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def fit_size(w: int, h: int, max_side: int = 1024, multiple: int = 16) -> tuple[int, int]:
    """Scale (w, h) so the long side is max_side, both rounded down to `multiple`."""
    scale = max_side / max(w, h)
    nw = max(multiple, int(w * scale) // multiple * multiple)
    nh = max(multiple, int(h * scale) // multiple * multiple)
    return nw, nh


def resize_for_model(img: Image.Image, max_side: int = 1024, multiple: int = 16) -> Image.Image:
    return img.resize(fit_size(*img.size, max_side, multiple), Image.LANCZOS)


def to_float(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0


def to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8))


# --------------------------------------------------------------------------- #
# Garment preparation (flat-lay on a plain background)
# --------------------------------------------------------------------------- #

def border_pixels(arr: np.ndarray, width: int = 8) -> np.ndarray:
    return np.concatenate([
        arr[:width].reshape(-1, 3), arr[-width:].reshape(-1, 3),
        arr[:, :width].reshape(-1, 3), arr[:, -width:].reshape(-1, 3),
    ])


def remove_plain_background(img: Image.Image, tol_de: float = 12.0) -> np.ndarray:
    """Boolean garment mask for a flat-lay shot on a plain background.

    Background colour = median of the border; pixels further than `tol_de`
    (CIE76 in Lab) are foreground. Keeps the largest component and fills holes,
    so a white print on a white tee isn't cut out.
    """
    arr = to_float(img)
    lab = color.rgb2lab(arr)
    bg = np.median(border_pixels(lab), axis=0)
    dist = np.linalg.norm(lab - bg, axis=-1)
    fg = dist > tol_de
    fg = ndimage.binary_opening(fg, structure=morphology.disk(2))
    # bridge thin background-coloured gaps (white stripes on a white backdrop)
    close_r = max(3, int(0.01 * max(fg.shape)))
    # pad by edge replication so closing doesn't erode a garment that touches the border
    fg = np.pad(fg, close_r, mode="edge")
    fg = ndimage.binary_closing(fg, structure=morphology.disk(close_r))[close_r:-close_r, close_r:-close_r]
    labels = measure.label(fg)
    if labels.max() == 0:
        return np.zeros(fg.shape, dtype=bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    # keep every sizeable piece (drop specks of dust/lint), not just the largest
    keep = np.flatnonzero(sizes >= 0.05 * sizes.max())
    return ndimage.binary_fill_holes(np.isin(labels, keep))


def white_balance_from_background(img: Image.Image, garment_mask: np.ndarray) -> Image.Image:
    """Scale channels so the background becomes neutral grey (gray-world on bg only)."""
    arr = to_float(img)
    bg = arr[~garment_mask]
    if bg.size == 0:
        return img
    means = bg.mean(axis=0)
    gains = means.mean() / np.maximum(means, 1e-4)
    return to_pil(arr * gains)


def crop_to_mask(img: Image.Image, mask: np.ndarray, pad_frac: float = 0.06,
                 fill=(255, 255, 255)) -> tuple[Image.Image, np.ndarray]:
    """Crop to the mask's bounding box (+ padding) and paint the background `fill`."""
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        raise ValueError("empty garment mask")
    h, w = mask.shape
    pad = int(max(h, w) * pad_frac)
    y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + pad + 1)
    arr = np.asarray(img.convert("RGB")).copy()
    arr[~mask] = fill
    return Image.fromarray(arr[y0:y1, x0:x1]), mask[y0:y1, x0:x1]


def blur_score(img: Image.Image) -> float:
    """Variance of the Laplacian on a 512px greyscale copy; low = blurry."""
    small = img.copy()
    small.thumbnail((512, 512))
    grey = color.rgb2gray(to_float(small))
    return float(filters.laplace(grey).var() * 1e4)


def touches_edge(mask: np.ndarray, margin: int = 2) -> bool:
    return bool(mask[:margin].any() or mask[-margin:].any()
                or mask[:, :margin].any() or mask[:, -margin:].any())


@dataclass
class GarmentCheck:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    blur: float = 0.0
    coverage: float = 0.0


def check_garment(img: Image.Image, mask: np.ndarray, min_blur: float = 2.0,
                  min_cov: float = 0.05, max_cov: float = 0.95) -> GarmentCheck:
    """Fail fast on bad uploads (INPUT_INVALID in the API taxonomy)."""
    reasons = []
    b = blur_score(img)
    cov = float(mask.mean())
    if b < min_blur:
        reasons.append("BLURRY")
    if cov < min_cov:
        reasons.append("GARMENT_NOT_FOUND")
    elif cov > max_cov:
        reasons.append("BACKGROUND_NOT_PLAIN")
    if touches_edge(mask):
        reasons.append("GARMENT_CUT_OFF")
    return GarmentCheck(ok=not reasons, reasons=reasons, blur=round(b, 2), coverage=round(cov, 3))


def prepare_garment(img: Image.Image, tol_de: float = 12.0) -> tuple[Image.Image, np.ndarray, GarmentCheck]:
    mask = remove_plain_background(img, tol_de)
    check = check_garment(img, mask)
    if not mask.any():
        return img, mask, check
    balanced = white_balance_from_background(img, mask)
    crop, crop_mask = crop_to_mask(balanced, mask)
    return crop, crop_mask, check


# --------------------------------------------------------------------------- #
# Clothing masks on the house-model bases
# --------------------------------------------------------------------------- #

# Label ids of the SegFormer "clothes" human-parsing model used in notebook 01
# (ATR-style labels). Research-only until its licence is cleared, see licence register.
SEG_LABELS = {
    "background": 0, "hat": 1, "hair": 2, "sunglasses": 3, "upper_clothes": 4,
    "skirt": 5, "pants": 6, "dress": 7, "belt": 8, "left_shoe": 9, "right_shoe": 10,
    "face": 11, "left_leg": 12, "right_leg": 13, "left_arm": 14, "right_arm": 15,
    "bag": 16, "scarf": 17,
}

REGION_LABELS = {
    "upper": ["upper_clothes", "scarf"],
    "lower": ["pants", "skirt", "belt"],
    "full": ["upper_clothes", "scarf", "pants", "skirt", "dress", "belt"],
}

# Which mask each garment category swaps.
CATEGORY_REGION = {
    "tshirt": "upper", "shirt": "upper", "top": "upper", "kurta": "upper",
    "sleeveless": "upper", "jacket": "upper",
    "jeans": "lower", "trousers": "lower", "skirt": "lower",
    "dress": "full",
}


def region_mask(label_map: np.ndarray, region: str, include_arms: bool = False) -> np.ndarray:
    """Boolean mask for a region from a per-pixel label map.

    include_arms: needed when the garment's sleeves are longer than the base outfit's
    (e.g. a full-sleeve shirt on a t-shirt base), so the model can paint over bare arms.
    Hands are not separate labels here; the feathered edge plus the hard composite keep them.
    """
    names = list(REGION_LABELS[region])
    if include_arms:
        names += ["left_arm", "right_arm"]
    ids = [SEG_LABELS[n] for n in names]
    return np.isin(label_map, ids)


def dilate_and_feather(mask: np.ndarray, dilate_px: int = 12, feather_px: int = 8) -> np.ndarray:
    """Grow the mask (so the new garment can be slightly larger) and soften its edge.

    Returns float32 in [0, 1]. A pixel well outside the grown mask is exactly 0.
    """
    grown = ndimage.binary_dilation(mask, structure=morphology.disk(dilate_px)) if dilate_px else mask
    if not feather_px:
        return grown.astype(np.float32)
    # 1 inside, linear ramp to 0 over `feather_px` outside, exactly 0 beyond
    dist_out = ndimage.distance_transform_edt(~grown)
    return np.clip(1.0 - dist_out / feather_px, 0.0, 1.0).astype(np.float32)


def mask_to_pil(mask: np.ndarray) -> Image.Image:
    """White = repaint, black = keep (diffusers inpaint convention)."""
    return Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), mode="L")


def composite(base: Image.Image, generated: Image.Image, alpha: np.ndarray) -> Image.Image:
    """out = base*(1-a) + gen*a. Outside the mask the result is exactly the base."""
    if generated.size != base.size:
        generated = generated.resize(base.size, Image.LANCZOS)
    b, g = to_float(base), to_float(generated)
    a = alpha[..., None].astype(np.float32)
    out = b * (1.0 - a) + g * a
    # bit-exact copy where alpha == 0 (float round-trip could otherwise differ by 1/255)
    out_u8 = np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8)
    keep = alpha <= 0.0
    out_u8[keep] = np.asarray(base.convert("RGB"))[keep]
    return Image.fromarray(out_u8)


def overlay_mask(img: Image.Image, mask: np.ndarray, rgb=(255, 0, 80), opacity: float = 0.45) -> Image.Image:
    arr = to_float(img)
    tint = np.array(rgb, dtype=np.float32) / 255.0
    a = (np.clip(mask, 0, 1) * opacity)[..., None]
    return to_pil(arr * (1 - a) + tint * a)


# --------------------------------------------------------------------------- #
# Scoring (docs/architecture/03#ranking)
# --------------------------------------------------------------------------- #

def _kmeans(x: np.ndarray, k: int, iters: int = 20, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    k = min(k, len(x))
    centres = x[rng.choice(len(x), size=k, replace=False)]
    for _ in range(iters):
        d = ((x[:, None, :] - centres[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        new = np.array([x[lab == i].mean(0) if (lab == i).any() else centres[i] for i in range(k)])
        if np.allclose(new, centres, atol=1e-3):
            break
        centres = new
    weights = np.bincount(lab, minlength=k).astype(np.float64)
    return centres, weights / weights.sum()


def dominant_palette(img: Image.Image, mask: np.ndarray, k: int = 5,
                     max_pixels: int = 20000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """k dominant Lab colours (and their weights) inside `mask`."""
    if img.size != (mask.shape[1], mask.shape[0]):
        raise ValueError("image and mask size differ")
    lab = color.rgb2lab(to_float(img))[mask > 0.5]
    if len(lab) == 0:
        raise ValueError("empty mask")
    if len(lab) > max_pixels:
        lab = lab[np.random.default_rng(seed).choice(len(lab), max_pixels, replace=False)]
    return _kmeans(lab, k, seed=seed)


def palette_delta_e(pa: np.ndarray, wa: np.ndarray, pb: np.ndarray, wb: np.ndarray) -> float:
    """Symmetric, weight-averaged nearest-colour CIEDE2000 between two palettes."""
    d = color.deltaE_ciede2000(pa[:, None, :], pb[None, :, :])
    a_to_b = (d.min(1) * wa).sum()
    b_to_a = (d.min(0) * wb).sum()
    return float((a_to_b + b_to_a) / 2.0)


def colour_delta_e(garment: Image.Image, garment_mask: np.ndarray,
                   output: Image.Image, output_mask: np.ndarray, k: int = 5) -> float:
    pa, wa = dominant_palette(garment, garment_mask, k)
    pb, wb = dominant_palette(output, output_mask, k)
    return palette_delta_e(pa, wa, pb, wb)


def leak_score(base: Image.Image, output: Image.Image, alpha: np.ndarray) -> float:
    """Mean abs difference (0..1) outside the mask. ~0 if compositing is right."""
    outside = alpha <= 0.0
    if not outside.any():
        return 0.0
    diff = np.abs(to_float(base) - to_float(output)).mean(-1)
    return float(diff[outside].mean())


def crop_box(mask: np.ndarray, pad: int = 8) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(mask > 0.5)
    h, w = mask.shape
    return (max(0, xs.min() - pad), max(0, ys.min() - pad),
            min(w, xs.max() + pad + 1), min(h, ys.max() + pad + 1))


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.ravel(a).astype(np.float64), np.ravel(b).astype(np.float64)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


DEFAULT_WEIGHTS = {"colour": 0.5, "pattern": 0.5, "leak_penalty": 10.0}


def total_score(colour_de: float, pattern_sim: float | None, leak: float,
                weights: dict = DEFAULT_WEIGHTS) -> float:
    """Combine signals into 0..1. Weights get tuned on the eval set."""
    colour_term = max(0.0, 1.0 - colour_de / 30.0)          # dE 0 → 1.0, dE ≥30 → 0
    if pattern_sim is None:
        s = colour_term
    else:
        pattern_term = float(np.clip((pattern_sim - 0.5) / 0.5, 0.0, 1.0))
        s = weights["colour"] * colour_term + weights["pattern"] * pattern_term
    s -= weights["leak_penalty"] * leak
    return round(float(np.clip(s, 0.0, 1.0)), 4)


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

@dataclass
class HouseModelSpec:
    name: str = "Arjun"
    person: str = ("a 30 year old North Indian man, 6 feet tall, athletic build, "
                   "warm medium-brown skin, short neat black hair, clean shaven, calm neutral expression")
    outfit: str = "a plain fitted heather-grey crew-neck t-shirt and slim charcoal trousers, white sneakers"
    scene: str = ("professional e-commerce fashion catalog photo, full body, standing straight, arms relaxed "
                  "at sides, seamless light grey studio backdrop, soft even studio lighting, "
                  "shot on 85mm lens at chest height, sharp focus, photorealistic, natural skin texture")

    def identity_prompt(self) -> str:
        return f"{self.scene}. The model is {self.person}, wearing {self.outfit}. Front view."

    def pose_prompt(self, angle: str) -> str:
        return (f"The same man from the reference image, same face, same body, same clothes. "
                f"{self.scene}. {ANGLE_PHRASES[angle]}. Wearing {self.outfit}.")


def swap_prompt(category: str, angle: str) -> str:
    return (f"The man is wearing the {category} from the reference image, exactly as shown: "
            f"same colour, same print and logo placement, same neckline, sleeves and buttons. "
            f"Natural fabric folds and fit, consistent studio lighting, {ANGLE_PHRASES[angle]}.")


# --------------------------------------------------------------------------- #
# Grids and reporting
# --------------------------------------------------------------------------- #

def make_grid(images: list[Image.Image], labels: list[str] | None = None,
              cols: int = 4, cell: int = 320) -> Image.Image:
    labels = labels or [""] * len(images)
    rows = max(1, -(-len(images) // cols))
    label_h = 22
    grid = Image.new("RGB", (cols * cell, rows * (cell + label_h)), "white")
    draw = ImageDraw.Draw(grid)
    for i, (im, lab) in enumerate(zip(images, labels)):
        im = im.convert("RGB").copy()
        im.thumbnail((cell, cell))
        x, y = (i % cols) * cell, (i // cols) * (cell + label_h)
        grid.paste(im, (x + (cell - im.width) // 2, y))
        draw.text((x + 4, y + cell + 4), str(lab)[:48], fill="black")
    return grid


SCORE_COLUMNS = [
    "garment_id", "category", "difficulty", "angle", "candidate", "seed",
    "colour_dE", "pattern_sim", "leak", "total", "pass", "fail_reason",
    "sec_per_img", "peak_vram_gb", "engine",
]


_FLOAT_COLUMNS = ["colour_dE", "pattern_sim", "leak", "total", "sec_per_img", "peak_vram_gb"]
_INT_COLUMNS = ["candidate", "seed"]
_TEXT_COLUMNS = ["garment_id", "category", "difficulty", "angle", "pass", "fail_reason", "engine"]


def normalize_scores(df):
    """Fix dtypes after concat-with-empty / CSV round-trips (blank cells come back as NaN)."""
    df = df.reindex(columns=SCORE_COLUMNS).copy()
    for c in _FLOAT_COLUMNS:
        df[c] = df[c].astype("float64")
    for c in _INT_COLUMNS:
        df[c] = df[c].astype("Int64")
    for c in _TEXT_COLUMNS:
        df[c] = df[c].astype("object").where(df[c].notna(), "").astype(str)
    return df


def summarize(df) -> dict:
    """Pass rates and the Phase-0 exit verdict from a filled-in score sheet.

    Uses the candidate the reviewer marked (pass in Y/N) with the best `total`
    per (garment, angle): the seller sees the top candidates, so one good one is enough.
    """
    import pandas as pd

    reviewed = df[df["pass"].isin(["Y", "N"])].copy()
    if reviewed.empty:
        return {"reviewed": 0, "verdict": "NOT_REVIEWED"}
    reviewed["passed"] = reviewed["pass"] == "Y"
    per_angle = (reviewed.sort_values("total", ascending=False)
                 .groupby(["garment_id", "angle"], as_index=False)
                 .agg(category=("category", "first"), difficulty=("difficulty", "first"),
                      passed=("passed", "max")))
    by_cat = per_angle.groupby("category")["passed"].mean().round(3).to_dict()
    by_angle = per_angle.groupby("angle")["passed"].mean().round(3).to_dict()
    gate = per_angle[(per_angle["difficulty"] == "simple")
                     & (per_angle["category"].map(CATEGORY_REGION).eq("upper"))
                     & (per_angle["angle"].isin(EXIT_ANGLES))]
    gate_rate = float(gate["passed"].mean()) if len(gate) else float("nan")
    reasons = (reviewed.loc[~reviewed["passed"], "fail_reason"].fillna("OTHER")
               .value_counts().to_dict())
    verdict = ("NOT_ENOUGH_DATA" if len(gate) == 0 or pd.isna(gate_rate)
               else "PASS" if gate_rate >= EXIT_THRESHOLD else "FAIL")
    return {
        "reviewed": int(len(per_angle)),
        "pass_rate_by_category": by_cat,
        "pass_rate_by_angle": by_angle,
        "exit_gate_items": int(len(gate)),
        "exit_gate_pass_rate": round(gate_rate, 3) if len(gate) else None,
        "verdict": verdict,
        "top_fail_reasons": reasons,
        "median_sec_per_img": float(df["sec_per_img"].median()) if "sec_per_img" in df else None,
    }


def save_json(obj, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, default=str))
