import json
import random
from pathlib import Path
from typing import Callable, Optional

from eval.eval_runner import ERROR_FIELD_ALIASES, SYNTHETIC_NOISE_FIELDS, SEVERITY_ORDER

PROJECT_ROOT = Path(__file__).parent.parent
EVAL_DIR = PROJECT_ROOT / "eval"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

RESULTS_PATH = EVAL_DIR / "results.json"
ROUND1_RESULTS_PATH = EVAL_DIR / "round1_results.json"


def load_results() -> dict:
    with open(RESULTS_PATH) as f:
        return json.load(f)


def load_round1_results() -> dict:
    with open(ROUND1_RESULTS_PATH) as f:
        return json.load(f)


def load_matched_round1(results: dict | None = None) -> dict:
    """round1_results.json entries restricted to the auction_ids that made
    it into results.json's rows -- keeps every analysis in this package
    working from the exact same population the project's own headline
    numbers (verdict_accuracy, per_field_metrics) are computed from, so
    numbers are directly comparable."""
    results = results if results is not None else load_results()
    auction_ids = {r["auction_id"] for r in results["rows"]}
    round1 = load_round1_results()
    return {aid: entry for aid, entry in round1.items() if aid in auction_ids}


def build_row_records(round1_matched: dict) -> tuple[list[dict], int]:
    """Flattens each matched round1_results.json entry into a row record
    carrying every flag verify_listing() computed *before* CONFIDENCE_FLOOR
    filtering (VerificationSummary.all_flags_before_floor), each labeled
    against that row's own ground truth:

      label=1 -- flag.field_name matches the row's true injected
                 error_field (a real detection instance)
      label=0 -- a genuine false positive (mirrors eval_runner.py's own
                 per_field_metrics fp definition exactly)

    Flags on SYNTHETIC_NOISE_FIELDS are dropped when they don't match --
    same as eval_runner.py's scoring -- since they're structural artifacts
    (limited photo sampling, VIN decode gaps) rather than a real signal
    about the check's confidence-vs-correctness behavior.

    Using all_flags_before_floor instead of the already-floor-filtered
    `flags` list is deliberate: it lets calibration/threshold analyses see
    the full confidence range (down to 0.3), not just the >=0.70 slice
    that survived the current floor -- the only way to test whether
    *lowering* the floor would recover real signal, not just whether
    raising it further would help.
    """
    rows = []
    skipped = 0
    for auction_id, entry in round1_matched.items():
        vs = entry.get("verification_summary")
        if not vs or "all_flags_before_floor" not in vs:
            skipped += 1
            continue
        error_field = entry["error_field"]
        aliases = ERROR_FIELD_ALIASES.get(error_field, [error_field])
        flags = []
        for item in vs["all_flags_before_floor"]:
            f = item["flag"]
            matches = f["field_name"] in aliases
            if not matches and f["field_name"] in SYNTHETIC_NOISE_FIELDS:
                continue
            flags.append({
                "field_name": f["field_name"],
                "confidence": f["confidence"],
                "severity": f["severity"],
                "label": 1 if matches else 0,
            })
        rows.append({
            "auction_id": auction_id,
            "error_type": entry["error_type"],
            "error_field": error_field,
            "expected_flag_severity": entry["expected_flag_severity"],
            "reassigned": entry.get("reassigned"),
            "prose_patch_applied": entry.get("prose_patch_applied"),
            "flags": flags,
        })
    return rows, skipped


def flatten_flag_observations(rows: list[dict]) -> list[dict]:
    """One record per flag (not per row) -- the shape calibration.py needs."""
    observations = []
    for row in rows:
        for f in row["flags"]:
            observations.append({
                "auction_id": row["auction_id"],
                "error_type": row["error_type"],
                "expected_flag_severity": row["expected_flag_severity"],
                **f,
            })
    return observations


def row_caught_at_threshold(row: dict, threshold: float) -> bool:
    """Same 'caught' definition eval_runner.py uses (a label=1 flag whose
    severity is at or above what's expected), but at an arbitrary
    confidence threshold instead of the fixed CONFIDENCE_FLOOR."""
    expected_severity = row["expected_flag_severity"]
    return any(
        f["label"] == 1
        and f["confidence"] >= threshold
        and SEVERITY_ORDER.get(f["severity"], 99) <= SEVERITY_ORDER.get(expected_severity, 99)
        for f in row["flags"]
    )


def row_fp_count_at_threshold(row: dict, threshold: float) -> int:
    """Same per_field_metrics fp definition eval_runner.py uses -- every
    label=0 flag on this row (any field) is counted against this row's
    OWN error_type, not the flag's own field. That's how the existing
    per-error-type precision numbers are already computed; kept identical
    here so threshold-swept numbers are directly comparable to them."""
    return sum(1 for f in row["flags"] if f["label"] == 0 and f["confidence"] >= threshold)


def bootstrap_ci(
    values: list[float],
    statistic_fn: Optional[Callable[[list[float]], float]] = None,
    n_iterations: int = 5000,
    ci: float = 0.95,
    seed: int = 0,
) -> dict:
    """Percentile-bootstrap confidence interval for any statistic computed
    over a list of numbers (defaults to the mean, e.g. for a 0/1-coded
    list this is exactly a proportion like recall or verdict_accuracy).

    Resamples `values` WITH replacement (same size as the original list)
    `n_iterations` times, recomputes `statistic_fn` on each resample, and
    takes the (1-ci)/2 and 1-(1-ci)/2 percentiles of the resulting
    distribution as the interval bounds -- the standard "percentile
    bootstrap" method, appropriate here since these statistics (means of
    0/1 data at n in the tens-to-hundreds) aren't badly skewed. seed=0
    matches this project's existing reproducible-randomness convention
    (see corpus/seed_verified_community_errors.py).

    Returns None for ci_low/ci_high/se if `values` is empty -- callers
    should treat that as "not enough data," not as a real interval of
    width zero."""
    if statistic_fn is None:
        statistic_fn = lambda vs: sum(vs) / len(vs)  # noqa: E731

    n = len(values)
    if n == 0:
        return {
            "point_estimate": None, "ci_low": None, "ci_high": None,
            "bootstrap_se": None, "n_iterations": n_iterations, "n": 0,
        }

    point_estimate = statistic_fn(values)
    rng = random.Random(seed)
    resample_stats = []
    for _ in range(n_iterations):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        resample_stats.append(statistic_fn(resample))
    resample_stats.sort()

    lower_idx = int((1 - ci) / 2 * n_iterations)
    upper_idx = int((1 - (1 - ci) / 2) * n_iterations) - 1
    upper_idx = min(upper_idx, n_iterations - 1)
    mean_resample = sum(resample_stats) / n_iterations
    variance = sum((s - mean_resample) ** 2 for s in resample_stats) / (n_iterations - 1)

    return {
        "point_estimate": round(point_estimate, 4),
        "ci_low": round(resample_stats[lower_idx], 4),
        "ci_high": round(resample_stats[upper_idx], 4),
        "bootstrap_se": round(variance ** 0.5, 4),
        "ci_level": ci,
        "n_iterations": n_iterations,
        "n": n,
    }


def roc_curve_and_auc(labels: list[int], scores: list[float]) -> dict:
    """Manual ROC curve + AUC via the standard rank/trapezoidal method (no
    scikit-learn dependency -- this project doesn't otherwise use it, and
    the algorithm is short enough to implement directly and explain).

    For each distinct score value, in descending order, treat it as the
    classification threshold and plot (false-positive rate, true-positive
    rate) at that point -- ties (identical scores) are grouped and moved
    through together, exactly matching how scikit-learn's roc_curve
    handles them. AUC is the trapezoidal-rule area under the resulting
    step function; this is mathematically identical to the more common
    "probability a random positive ranks above a random negative"
    definition of AUC, just computed geometrically instead of by counting
    pairs (equivalent, cheaper at this n).

    labels must be 0/1 (1 = real positive case). Returns auc=None with a
    note if there are no positives or no negatives -- AUC is undefined in
    that case, not zero or one."""
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return {
            "auc": None, "fpr": [], "tpr": [], "thresholds": [],
            "n_positive": n_pos, "n_negative": n_neg,
            "note": "AUC undefined -- no positive or no negative examples for this check.",
        }

    pairs = sorted(zip(scores, labels), key=lambda p: -p[0])
    fpr_points = [0.0]
    tpr_points = [0.0]
    thresholds = [float("inf")]
    tp = fp = 0
    i = 0
    while i < len(pairs):
        threshold = pairs[i][0]
        j = i
        while j < len(pairs) and pairs[j][0] == threshold:
            if pairs[j][1] == 1:
                tp += 1
            else:
                fp += 1
            j += 1
        tpr_points.append(tp / n_pos)
        fpr_points.append(fp / n_neg)
        thresholds.append(threshold)
        i = j

    auc = sum(
        (fpr_points[k] - fpr_points[k - 1]) * (tpr_points[k] + tpr_points[k - 1]) / 2
        for k in range(1, len(fpr_points))
    )

    return {
        "auc": round(auc, 4),
        "fpr": [round(x, 4) for x in fpr_points],
        "tpr": [round(x, 4) for x in tpr_points],
        "thresholds": thresholds,
        "n_positive": n_pos,
        "n_negative": n_neg,
    }


def write_json(obj: dict, filename: str) -> Path:
    path = OUTPUT_DIR / filename
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)
    return path
