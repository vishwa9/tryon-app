"""CPU tests for research/phase0_utils.py on synthetic images (no models, no GPU).

Run from the repo root:  python -m pytest research/tests -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import phase0_utils as u  # noqa: E402


def flat_lay(colour=(200, 30, 40), bg=(235, 235, 232), size=(600, 700), stripe=False):
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    # crude t-shirt: body + sleeves, away from the border
    d.rectangle([180, 180, 420, 600], fill=colour)
    d.polygon([(180, 180), (90, 280), (140, 330), (180, 280)], fill=colour)
    d.polygon([(420, 180), (510, 280), (460, 330), (420, 280)], fill=colour)
    if stripe:
        for y in range(200, 600, 40):
            d.rectangle([180, y, 420, y + 12], fill=(250, 250, 250))
    return img


def test_garment_ref_for_angle():
    assert u.garment_ref_for_angle("front", False) == ("front", None)
    assert u.garment_ref_for_angle("three_quarter_left", False) == ("front", None)
    assert u.garment_ref_for_angle("back", True) == ("back", None)
    assert u.garment_ref_for_angle("back", False) == (None, "NO_BACK_PHOTO")
    with pytest.raises(ValueError):
        u.garment_ref_for_angle("top_down", True)


def test_fit_size_multiple_of_16():
    w, h = u.fit_size(3000, 4000, max_side=1024)
    assert h == 1024 and w % 16 == 0 and h % 16 == 0 and w <= 768


def test_background_removal_finds_garment_and_keeps_white_stripes():
    img = flat_lay(stripe=True)
    mask = u.remove_plain_background(img)
    assert mask[400, 300]          # inside body
    assert mask[212, 300]          # on a white stripe: holes filled, not cut out
    assert not mask[20, 20]        # background corner
    assert 0.15 < mask.mean() < 0.5


def test_check_garment_flags_problems():
    img = flat_lay()
    good = u.check_garment(img, u.remove_plain_background(img))
    assert good.ok, good.reasons

    blurry = img.filter(ImageFilter.GaussianBlur(12))
    assert "BLURRY" in u.check_garment(blurry, u.remove_plain_background(blurry)).reasons

    cut = Image.new("RGB", (600, 700), (235, 235, 232))
    ImageDraw.Draw(cut).rectangle([0, 200, 400, 600], fill=(20, 60, 160))
    assert "GARMENT_CUT_OFF" in u.check_garment(cut, u.remove_plain_background(cut)).reasons

    empty = Image.new("RGB", (600, 700), (235, 235, 232))
    assert "GARMENT_NOT_FOUND" in u.check_garment(empty, u.remove_plain_background(empty)).reasons


def test_prepare_garment_crops_and_whitens_background():
    crop, cmask, check = u.prepare_garment(flat_lay())
    assert check.ok
    assert crop.size[0] < 600 and crop.size == (cmask.shape[1], cmask.shape[0])
    assert np.asarray(crop)[0, 0].tolist() == [255, 255, 255]


def test_white_balance_neutralises_tinted_background():
    img = flat_lay(bg=(240, 225, 200))  # warm cast
    out = np.asarray(u.white_balance_from_background(img, u.remove_plain_background(img))).astype(float)
    corner = out[5:40, 5:40].reshape(-1, 3).mean(0)
    assert corner.max() - corner.min() < 3


def test_region_mask_and_arms():
    lm = np.zeros((10, 10), dtype=np.int64)
    lm[2:5, 3:7] = u.SEG_LABELS["upper_clothes"]
    lm[2:5, 1:3] = u.SEG_LABELS["left_arm"]
    lm[6:9, 3:7] = u.SEG_LABELS["pants"]
    lm[0:2, 4:6] = u.SEG_LABELS["face"]
    up = u.region_mask(lm, "upper")
    assert up.sum() == 12 and not up[0, 4]
    assert u.region_mask(lm, "upper", include_arms=True).sum() == 18
    assert u.region_mask(lm, "lower").sum() == 12
    assert u.region_mask(lm, "full").sum() == 24


def test_feather_is_one_inside_ramps_and_zero_far_away():
    m = np.zeros((100, 100), bool)
    m[40:60, 40:60] = True
    a = u.dilate_and_feather(m, dilate_px=4, feather_px=6)
    assert a.dtype == np.float32
    assert a[50, 50] == 1.0 and a[50, 36] == 1.0      # inside the grown mask
    assert 0.0 < a[50, 33] < 1.0                       # ramp
    assert a[50, 20] == 0.0 and a[0, 0] == 0.0         # beyond feather: exactly 0
    assert np.all(np.diff(a[50, 20:50]) >= -1e-6)      # monotone ramp in


def test_composite_is_bit_exact_outside_mask():
    rng = np.random.default_rng(0)
    base = Image.fromarray(rng.integers(0, 256, (64, 64, 3), dtype=np.uint8))
    gen = Image.fromarray(rng.integers(0, 256, (64, 64, 3), dtype=np.uint8))
    m = np.zeros((64, 64), bool)
    m[20:40, 20:40] = True
    alpha = u.dilate_and_feather(m, 2, 4)
    out = u.composite(base, gen, alpha)
    outside = alpha == 0
    assert np.array_equal(np.asarray(out)[outside], np.asarray(base)[outside])
    assert np.array_equal(np.asarray(out)[30, 30], np.asarray(gen)[30, 30])
    assert u.leak_score(base, out, alpha) == 0.0
    # a broken composite (raw generation) shows up as leak
    assert u.leak_score(base, gen, alpha) > 0.1


def test_composite_resizes_generation():
    base = Image.new("RGB", (64, 48), (10, 10, 10))
    gen = Image.new("RGB", (128, 96), (200, 200, 200))
    alpha = np.zeros((48, 64), np.float32)
    alpha[10:20, 10:20] = 1
    out = np.asarray(u.composite(base, gen, alpha))
    assert out[15, 15].tolist() == [200, 200, 200] and out[0, 0].tolist() == [10, 10, 10]


def test_colour_delta_e_same_vs_different():
    red, mred = u.prepare_garment(flat_lay((200, 30, 40)))[:2]
    red2, mred2 = u.prepare_garment(flat_lay((198, 32, 42)))[:2]
    blue, mblue = u.prepare_garment(flat_lay((30, 60, 190)))[:2]
    same = u.colour_delta_e(red, mred, red2, mred2)
    diff = u.colour_delta_e(red, mred, blue, mblue)
    assert same < 3.0
    assert diff > 30.0


def test_colour_delta_e_rejects_size_mismatch():
    img = flat_lay()
    with pytest.raises(ValueError):
        u.dominant_palette(img, np.ones((10, 10), bool))


def test_total_score_orders_sensibly():
    good = u.total_score(2.0, 0.92, 0.0)
    bad_colour = u.total_score(25.0, 0.92, 0.0)
    bad_leak = u.total_score(2.0, 0.92, 0.05)
    assert good > bad_colour and good > bad_leak
    assert 0.0 <= u.total_score(100, 0.0, 1.0) <= u.total_score(0, None, 0) == 1.0


def test_cosine():
    assert u.cosine(np.array([1, 0]), np.array([1, 0])) == pytest.approx(1.0)
    assert u.cosine(np.array([1, 0]), np.array([0, 1])) == pytest.approx(0.0)


def test_prompts_mention_angle_and_reference():
    spec = u.HouseModelSpec()
    for a in u.ANGLES:
        p = spec.pose_prompt(a)
        assert u.ANGLE_PHRASES[a] in p and "reference" in p
    assert "kurta" in u.swap_prompt("kurta", "front")


def test_make_grid_shape():
    g = u.make_grid([flat_lay()] * 5, list("abcde"), cols=4, cell=100)
    assert g.size == (400, 2 * 122)


def _sheet(rows):
    return pd.DataFrame(rows, columns=u.SCORE_COLUMNS)


def test_summarize_uses_best_candidate_and_exit_gate():
    rows = []
    # 4 simple tops x front: 3 have a passing candidate, 1 doesn't -> 75% -> PASS
    for g in range(4):
        rows.append([f"g{g}", "tshirt", "simple", "front", 0, 1, 2, .9, 0, .9 - g * .01,
                     "Y" if g < 3 else "N", None if g < 3 else "COLOUR_MISMATCH", 20, 12, "klein"])
        rows.append([f"g{g}", "tshirt", "simple", "front", 1, 2, 9, .7, 0, .5, "N", "ARTEFACT_HANDS", 20, 12, "klein"])
    # hard items and back view don't count towards the gate
    rows.append(["h1", "dress", "hard", "front", 0, 1, 20, .5, 0, .2, "N", "SHAPE_WRONG", 22, 12, "klein"])
    rows.append(["g0", "tshirt", "simple", "back", 0, 1, 20, .5, 0, .2, "N", "PRINT_OR_LOGO_WRONG", 22, 12, "klein"])
    # unreviewed rows are ignored
    rows.append(["g9", "tshirt", "simple", "front", 0, 1, 2, .9, 0, .9, "", None, 20, 12, "klein"])
    s = u.summarize(_sheet(rows))
    assert s["exit_gate_items"] == 4
    assert s["exit_gate_pass_rate"] == 0.75
    assert s["verdict"] == "PASS"
    assert s["pass_rate_by_angle"]["back"] == 0.0
    assert s["top_fail_reasons"]["ARTEFACT_HANDS"] == 4


def test_summarize_fail_and_empty():
    rows = [[f"g{g}", "shirt", "simple", "three_quarter_left", 0, 1, 2, .9, 0, .8,
             "Y" if g == 0 else "N", "SHAPE_WRONG", 20, 12, "klein"] for g in range(3)]
    assert u.summarize(_sheet(rows))["verdict"] == "FAIL"
    assert u.summarize(_sheet([]))["verdict"] == "NOT_REVIEWED"


def test_normalize_scores_after_concat_and_csv_roundtrip(tmp_path):
    empty = pd.DataFrame(columns=u.SCORE_COLUMNS)
    new = pd.DataFrame([{"garment_id": "g01", "category": "tshirt", "difficulty": "simple", "angle": "front",
                         "candidate": 0, "seed": 11, "colour_dE": 2.5, "pattern_sim": 0.9, "leak": 0.0,
                         "total": 0.9, "pass": "", "fail_reason": "", "sec_per_img": 20.0,
                         "peak_vram_gb": 9.5, "engine": "x"}])
    df = u.normalize_scores(pd.concat([empty, new], ignore_index=True))
    assert df["total"].dtype == "float64" and df["candidate"].dtype == "Int64"
    assert "mean" in df.groupby("angle")["total"].describe().columns
    p = tmp_path / "s.csv"
    df.to_csv(p, index=False)
    back = u.normalize_scores(pd.read_csv(p))
    assert back.loc[0, "pass"] == "" and back.loc[0, "fail_reason"] == ""
    assert back.loc[0, "candidate"] == 0 and back["total"].dtype == "float64"
