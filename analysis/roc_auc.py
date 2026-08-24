from eval.eval_runner import ERROR_FIELD_ALIASES
from analysis.common import (
    load_results, load_matched_round1, build_row_records,
    roc_curve_and_auc, write_json,
)

CHECKS = sorted(ERROR_FIELD_ALIASES.keys())
LOW_RESOLUTION_THRESHOLD = 2  # <= this many distinct nonzero scores = low-resolution curve
MIN_RELIABLE_N_POSITIVE = 5  # below this, AUC is dominated by a handful of examples


def _labels_and_scores_for_check(rows: list[dict], field_name: str) -> tuple[list[int], list[float]]:
    labels = []
    scores = []
    for row in rows:
        labels.append(1 if row["error_field"] == field_name else 0)
        matching_flags = [f for f in row["flags"] if f["field_name"] == field_name]
        score = max((f["confidence"] for f in matching_flags), default=0.0)
        scores.append(score)
    return labels, scores


def run() -> dict:
    results = load_results()
    matched_round1 = load_matched_round1(results)
    rows, skipped = build_row_records(matched_round1)

    per_check = {}
    for field_name in CHECKS:
        labels, scores = _labels_and_scores_for_check(rows, field_name)
        roc = roc_curve_and_auc(labels, scores)
        n_distinct_nonzero = len({s for s in scores if s > 0})
        roc["low_resolution"] = n_distinct_nonzero <= LOW_RESOLUTION_THRESHOLD
        roc["n_distinct_confidence_values"] = n_distinct_nonzero
        roc["few_positive_examples"] = (roc["n_positive"] or 0) < MIN_RELIABLE_N_POSITIVE
        per_check[field_name] = roc

    flat_table = [
        {
            "field_name": field_name,
            "auc": d["auc"],
            "n_positive": d["n_positive"],
            "n_negative": d["n_negative"],
            "low_resolution": d["low_resolution"],
            "few_positive_examples": d["few_positive_examples"],
            "n_distinct_confidence_values": d["n_distinct_confidence_values"],
        }
        for field_name, d in per_check.items()
    ]

    output = {
        "analysis": "roc_auc_per_check",
        "source": "eval/round1_results.json (all_flags_before_floor) matched to eval/results.json's 497-row population",
        "n_rows_used": len(rows),
        "n_rows_skipped_missing_data": skipped,
        "note": (
            "AUC = probability this check's confidence score ranks a random "
            "real positive case above a random negative case; 0.5 = no "
            "better than chance, 1.0 = perfect ranking. low_resolution=true "
            "means this check has 2 or fewer distinct nonzero confidence "
            "values, so its 'curve' is really a coarse step function -- "
            f"treat its AUC as a rough estimate, not a precise one. "
            f"few_positive_examples=true means fewer than {MIN_RELIABLE_N_POSITIVE} "
            "ground-truth rows exist for that check at all (e.g. "
            "engine_cylinders has exactly 1) -- its AUC is dominated by a "
            "handful of examples and shouldn't be quoted as a stable number."
        ),
        "per_check": per_check,
        "flat_table": flat_table,
    }
    return output


if __name__ == "__main__":
    output = run()
    path = write_json(output, "roc_auc.json")
    print(f"ROC/AUC per check written to {path}")
    print("\nAUC per check (sorted, best first):")
    ranked = sorted(output["per_check"].items(), key=lambda kv: (kv[1]["auc"] is None, -(kv[1]["auc"] or 0)))
    for field_name, d in ranked:
        flags = []
        if d["low_resolution"]:
            flags.append("low-resolution")
        if d["few_positive_examples"]:
            flags.append("few positive examples")
        flag_str = f" ({', '.join(flags)})" if flags else ""
        print(f"  {field_name:22s} AUC={d['auc']}{flag_str}  "
              f"n_pos={d['n_positive']} n_neg={d['n_negative']} "
              f"distinct_conf_values={d['n_distinct_confidence_values']}")
