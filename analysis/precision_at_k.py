import argparse
import random
from collections import Counter

from agents.extraction_agent import ListingData
from agents.vin_agent import VINData
from core.verifier import verify_listing
from eval.eval_runner import ERROR_FIELD_ALIASES, SEVERITY_ORDER, _STUB_EDITORIAL
from analysis.common import load_results, load_matched_round1, write_json
from analysis.photo_sampling_tradeoff import K_VALUES, BOOTSTRAP_DRAWS, _build_photo, _filter_dup_pairs

CHECKS = {
    "missing_angle": {"field_name": "photo_angles", "error_type": "missing_angle"},
    "color_error": {"field_name": "color", "error_type": "color_error"},
}


def _flags_on_field(flags, field_name):
    return [f for f in flags if f.field_name == field_name]


def run(draws: int = BOOTSTRAP_DRAWS, seed: int = 0) -> dict:
    rng = random.Random(seed)
    results = load_results()
    matched_round1 = load_matched_round1(results)

    out = {}
    for check_name, spec in CHECKS.items():
        field_name = spec["field_name"]
        target_error_type = spec["error_type"]

        tp_by_k = {k: 0.0 for k in K_VALUES}
        fp_by_k = {k: 0.0 for k in K_VALUES}
        n_pos_rows = 0
        n_neg_rows = 0

        for r in results["rows"]:
            entry = matched_round1.get(r["auction_id"])
            if entry is None or not entry.get("photos"):
                continue
            is_positive = r["error_type"] == target_error_type
            error_field = r["error_field"]
            expected_severity = r["expected_flag_severity"]
            aliases = ERROR_FIELD_ALIASES.get(error_field, [error_field])

            listing = ListingData(**entry["listing_data"])
            vin = VINData(**entry["vin_data"])
            photos_full = [_build_photo(p) for p in entry["photos"]]
            dup_pairs_full = [
                (p["url_a"], p["url_b"], p["hamming_distance"])
                for p in (entry.get("duplicate_photo_pairs") or [])
            ]
            n = len(photos_full)
            if is_positive:
                n_pos_rows += 1
            else:
                n_neg_rows += 1

            for k in K_VALUES:
                k_eff = n if k == "full" else min(k, n)
                if k_eff >= n:
                    subsets, reps = [(photos_full, dup_pairs_full)], 1
                else:
                    subsets, reps = [], draws
                    for _ in range(draws):
                        idx = rng.sample(range(n), k_eff)
                        subset_photos = [photos_full[i] for i in idx]
                        subset_url_counts = Counter(p.image_url for p in subset_photos)
                        subset_dup_pairs = _filter_dup_pairs(dup_pairs_full, subset_url_counts)
                        subsets.append((subset_photos, subset_dup_pairs))

                for subset_photos, subset_dup_pairs in subsets:
                    flags, _ = verify_listing(listing, vin, subset_photos, _STUB_EDITORIAL, subset_dup_pairs)
                    field_flags = _flags_on_field(flags, field_name)
                    if not field_flags:
                        continue
                    if is_positive:
                        caught = any(
                            f.field_name in aliases and SEVERITY_ORDER.get(f.severity, 99) <= SEVERITY_ORDER.get(expected_severity, 99)
                            for f in field_flags
                        )
                        if caught:
                            tp_by_k[k] += 1.0 / reps
                    else:
                        fp_by_k[k] += 1.0 / reps

        curve = []
        for k in K_VALUES:
            tp, fp = tp_by_k[k], fp_by_k[k]
            precision = tp / (tp + fp) if (tp + fp) > 0 else None
            curve.append({
                "k": k, "tp": round(tp, 2), "fp": round(fp, 2),
                "precision": round(precision, 4) if precision is not None else None,
            })
        out[check_name] = {"field_name": field_name, "n_positive_rows": n_pos_rows, "n_negative_rows": n_neg_rows, "curve": curve}

    return {
        "analysis": "precision_at_k",
        "source": "eval/round1_results.json matched to eval/results.json's 497-row population",
        "method": (
            "Retrospective simulation: real verify_listing() rerun on random k-photo "
            "subsamples of every row's already-analyzed real photos (not just rows where "
            "that check's error was injected), counting true and false positives on the "
            "check's own flag field to get a check-level precision curve."
        ),
        "k_values": K_VALUES,
        "bootstrap_draws": draws,
        "seed": seed,
        "checks": out,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=BOOTSTRAP_DRAWS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    output = run(draws=args.draws, seed=args.seed)
    path = write_json(output, "precision_at_k.json")
    print(f"Precision-at-k written to {path}")
    for check_name, data in output["checks"].items():
        print(f"\n{check_name} (field={data['field_name']}, "
              f"n_positive={data['n_positive_rows']}, n_negative={data['n_negative_rows']}):")
        for point in data["curve"]:
            print(f"  k={point['k']!s:6} tp={point['tp']:<7} fp={point['fp']:<7} precision={point['precision']}")
