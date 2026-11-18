"""Synthetic temporal coordination pilot, v0.3.

Generate exact time-reversal pairs and matched static controls.
Run: python coordination_prototype.py --out output
No model calls, credentials or paid services are used.
"""

import argparse
import csv
import hashlib
import json
import random
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

VERSION = "0.3"
HIP = np.array([0.0, 1.0])
SHOULDER = np.array([0.0, 1.8])
LEG_LEN, ARM_LEN = 1.0, 0.8
LEG_AMP, ARM_AMP = 30.0, 45.0
MODES = ("ordered", "shuffled", "single")
PROMPT = (
    "The image shows a stick figure viewed from the side. The red segment "
    "is the arm and the blue segment is the opposite leg. Both swing at the "
    "same rhythm. When several frames are shown, read their numbered order "
    "from left to right. Treat the movement as a continuously repeating "
    "cycle, with the last frame followed by the first.\n"
    "Which segment's right-most peak occurs shortly before the other's "
    "(by less than half a cycle): ARM or LEG? Answer SAME if their peaks "
    "coincide. Judge the relative timing around the cycle, not simply which "
    "peak is first after the start of the image.\n"
    "Answer with exactly one word: ARM, LEG or SAME."
)


def validate_config(offsets, reps, catch, frames, cycles=1.0):
    if not offsets or any(not np.isfinite(x) or not 0 < x < 180 for x in offsets):
        raise ValueError("Offsets must be finite and strictly between 0 and 180 degrees.")
    if len(set(offsets)) != len(offsets):
        raise ValueError("Offsets must be unique.")
    if reps < 1 or catch < 0:
        raise ValueError("reps must be >= 1 and catch must be >= 0.")
    if frames < 8:
        raise ValueError("Use at least 8 frames per cycle.")
    if cycles != 1.0:
        raise ValueError("v0.3 supports exactly one cycle; use --cycles 1 or omit it.")


def swing(t_cycles, amp, phase_cycles):
    return amp * np.sin(2 * np.pi * (t_cycles + phase_cycles))


def reverse_cycle_indices(frames):
    """Reverse playback around a circle while retaining the same first pose."""
    return [0] + list(range(frames - 1, 0, -1))


def make_base(rng, offset_deg, frames):
    start = rng.random()
    leg_amp = LEG_AMP * rng.uniform(0.9, 1.1)
    arm_amp = ARM_AMP * rng.uniform(0.9, 1.1)
    t = np.arange(frames) / frames
    leg = swing(t, leg_amp, start)
    arm = swing(t, arm_amp, start - offset_deg / 360)
    return leg, arm, dict(start_phase=start, leg_amp=leg_amp, arm_amp=arm_amp)


def phase_difference_deg(leg, arm):
    """Phase at one cycle/window, valid for the generator's one-cycle signals.

    This is a numeric generator check, not a model result or a general-purpose
    movement estimator. Positive means ARM leads; negative means LEG leads.
    """
    leg, arm = np.asarray(leg, dtype=float), np.asarray(arm, dtype=float)
    if leg.ndim != 1 or leg.shape != arm.shape or len(leg) < 8:
        raise ValueError("Expected equal one-dimensional sequences with >= 8 samples.")
    if not np.isfinite(leg).all() or not np.isfinite(arm).all():
        raise ValueError("Non-finite angles.")
    basis = np.exp(-2j * np.pi * np.arange(len(leg)) / len(leg))
    coeff = [np.sum((x - x.mean()) * basis) for x in (leg, arm)]
    if any(abs(c) < 1e-10 for c in coeff):
        raise ValueError("Cannot measure phase at one cycle/window.")
    return float(np.rad2deg(np.angle(coeff[1] * np.conj(coeff[0]))))


def who_peaks_first(leg, arm):
    phase = phase_difference_deg(leg, arm)
    if abs(phase) < 1e-7:
        return "SAME"
    return "ARM" if phase > 0 else "LEG"


def build_trials(offsets, reps, catch, frames, seed):
    validate_config(offsets, reps, catch, frames)
    rng = random.Random(seed)
    normal = list(range(frames))
    reverse = reverse_cycle_indices(frames)
    trials = []
    group = 0
    specs = [(off, False) for off in offsets for _ in range(reps)]
    specs += [(0.0, True)] * catch
    for off, is_catch in specs:
        group += 1
        leg, arm, params = make_base(rng, off, frames)
        shuffle = normal.copy()
        # A shuffled control is shared by the two labels. It need not remove
        # every local adjacency; pairing removes its information about label.
        while shuffle in (normal, reverse):
            rng.shuffle(shuffle)
        single = [rng.randrange(frames)]
        directions = [("none", normal, "SAME")] if is_catch else [
            ("lag", normal, "LEG"), ("lead", reverse, "ARM")]
        for direction, ordered, answer in directions:
            trial = dict(group_id=f"g{group:04d}", offset_deg=off,
                         direction=direction, correct_answer=answer,
                         is_catch=is_catch, leg=leg, arm=arm, **params,
                         views={"ordered":ordered.copy(),
                                "shuffled":shuffle.copy(), "single":single.copy()})
            if who_peaks_first(leg[ordered], arm[ordered]) != answer:
                raise RuntimeError("Generator phase check failed.")
            trials.append(trial)
    rng.shuffle(trials)
    for i, trial in enumerate(trials, 1):
        trial["trial_id"] = f"trial_{i:03d}"
    return trials


def end_point(origin, length, angle_deg):
    a = np.deg2rad(angle_deg)
    return origin + length * np.array([np.sin(a), -np.cos(a)])


def draw_frame(ax, leg_angle, arm_angle, label):
    foot = end_point(HIP, LEG_LEN, leg_angle)
    hand = end_point(SHOULDER, ARM_LEN, arm_angle)
    ax.plot(*zip(HIP, SHOULDER), color="black", lw=3)
    ax.plot(*zip(HIP, foot), color="tab:blue", lw=4)
    ax.plot(*zip(SHOULDER, hand), color="tab:red", lw=4)
    ax.add_patch(plt.Circle(SHOULDER + [0, .25], .15, fill=False, lw=2))
    ax.axhline(0, color="grey", lw=1)
    ax.set(xlim=(-1, 1), ylim=(-.1, 2.3), aspect="equal")
    ax.axis("off")
    ax.set_title(str(label), fontsize=9)


def save_image(path, leg, arm):
    n = len(leg)
    fig, axes = plt.subplots(1, n, figsize=(n * 1.1, 2.2), squeeze=False)
    for i, ax in enumerate(axes[0]):
        draw_frame(ax, leg[i], arm[i], i + 1)
    fig.savefig(path, dpi=100, bbox_inches="tight", metadata={"Software":"coordination-prototype"})
    plt.close(fig)


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(trials, out):
    groups = {}
    for t in trials:
        groups.setdefault(t["group_id"], []).append(t)
    checked = 0
    for group in groups.values():
        if group[0]["is_catch"]:
            continue
        a, b = group
        if {a["correct_answer"], b["correct_answer"]} != {"ARM", "LEG"}:
            raise RuntimeError("Pair label imbalance.")
        for segment in ("leg", "arm"):
            x = a[segment][a["views"]["ordered"]]
            y = b[segment][b["views"]["ordered"]]
            if not np.array_equal(x[reverse_cycle_indices(len(x))], y):
                raise RuntimeError("Ordered sequences are not exact reversals.")
            if x[0] != y[0]:
                raise RuntimeError("Starting pose differs.")
        for mode in ("shuffled", "single"):
            paths = [out / "trials" / mode / (t["trial_id"] + ".png") for t in group]
            if sha256(paths[0]) != sha256(paths[1]):
                raise RuntimeError("Paired control images differ.")
        checked += 1
    return {"exact_reversal_pairs_checked":checked,
            "identical_start_pose":True, "paired_controls_byte_identical":True,
            "numeric_phase_check_passed":True,
            "model_evaluation_performed":False}


def generate(out, offsets=(15, 30, 60), reps=2, catch=2, frames=12, seed=1):
    validate_config(offsets, reps, catch, frames)
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Output directory is not empty: {out}. Choose a new --out directory.")
    out.mkdir(parents=True, exist_ok=True)
    for mode in MODES:
        (out / "trials" / mode).mkdir(parents=True)
    trials = build_trials(offsets, reps, catch, frames, seed)
    keys, responses, angles = [], [], []
    cache = {}
    for t in trials:
        for mode, idx in t["views"].items():
            relative = Path("trials") / mode / (t["trial_id"] + ".png")
            path = out / relative
            cache_key = (t["group_id"], mode)
            if mode != "ordered" and cache_key in cache:
                shutil.copyfile(cache[cache_key], path)
            else:
                save_image(path, t["leg"][idx], t["arm"][idx])
                cache[cache_key] = path
            keys.append(dict(trial_id=t["trial_id"], mode=mode,
                image=relative.as_posix(), group_id=t["group_id"],
                correct_answer=t["correct_answer"], is_catch=t["is_catch"],
                offset_deg=t["offset_deg"], direction=t["direction"],
                start_phase=t["start_phase"], leg_amp=t["leg_amp"], arm_amp=t["arm_amp"],
                canonical_frames=" ".join(str(i+1) for i in idx), sha256=sha256(path)))
            responses.append(dict(trial_id=t["trial_id"], mode=mode,
                image=relative.as_posix(), model="", model_version="", date_utc="",
                temperature="", model_answer="", notes=""))
            for position, index in enumerate(idx, 1):
                angles.append(dict(trial_id=t["trial_id"], mode=mode,
                    presented_frame=position, canonical_frame=index+1,
                    leg_deg=float(t["leg"][index]), arm_deg=float(t["arm"][index])))
    # Independent presentation order for each mode; no labels in response sheet.
    rng = random.Random(seed + 104729)
    scheduled = []
    for mode in MODES:
        batch = [r for r in responses if r["mode"] == mode]
        rng.shuffle(batch)
        for position, row in enumerate(batch, 1):
            scheduled.append(dict(presentation_order=position, **row))
    write_csv(out / "answer_key.csv", keys, list(keys[0]))
    write_csv(out / "responses.csv", scheduled, list(scheduled[0]))
    write_csv(out / "angles.csv", angles, list(angles[0]))
    (out / "prompt.txt").write_text(PROMPT + "\n", encoding="utf-8")
    report = {"version":VERSION, "seed":seed, "offsets_deg":list(offsets),
        "pairs_per_offset":reps, "catch_trials":catch, "frames":frames, "cycles":1,
        "stimuli_per_mode":len(trials), "total_images":len(keys),
        "answers_per_mode":{a:sum(t["correct_answer"]==a for t in trials)
                            for a in ("ARM", "LEG", "SAME")},
        **audit(trials, out)}
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offsets", type=float, nargs="+", default=[15, 30, 60])
    p.add_argument("--reps", type=int, default=2, help="independent pairs per offset")
    p.add_argument("--catch", type=int, default=2, help="zero-offset catch stimuli")
    p.add_argument("--frames", type=int, default=12)
    p.add_argument("--cycles", type=float, default=1.0, help="must be 1 in v0.3")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", type=Path, default=Path("output"))
    args = p.parse_args()
    try:
        validate_config(args.offsets, args.reps, args.catch, args.frames, args.cycles)
        result = generate(args.out, args.offsets, args.reps, args.catch, args.frames, args.seed)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
