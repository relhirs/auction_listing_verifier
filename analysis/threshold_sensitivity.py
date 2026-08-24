from collections import defaultdict

from analysis.common import (
    load_results, load_matched_round1, build_row_records,
    row_caught_at_threshold, row_fp_count_at_threshold, write_json,
)

THRESHOLD_SWEEP = [0.30, 0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]


def _metrics_at_threshold(rows: list[dict], threshold: float) -> dict:
    per_type = defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0})
    for row in rows:
        et = row["error_type"]
        if row_caught_at_threshold(row, threshold):
            per_type[et]["tp"] += 1
        else:
            per_type[et]["fn"] += 1
        per_type[et]["fp"] += row_fp_count_at_threshold(row, threshold)

    out = {}
    for et, c in per_type.items():
        tp, fn, fp = c["tp"], c["fn"], c["fp"]
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        f1 = (2 * precision * recall / (precision + recall)) if precision and recall and (precision + recall) else None
        out[et] = {
            "tp": tp, "fn": fn, "fp": fp,
            "precision": round(precision, 4) if precision is not None else None,
            "recall": round(recall, 4) if recall is not None else None,
            "f1": round(f1, 4) if f1 is not None else None,
        }
    return out


def run() -> dict:
    results = load_results()
    matched_round1 = load_matched_round1(results)
    rows, skipped = build_row_records(matched_round1)

    sweep_results = {t: _metrics_at_threshold(rows, t) for t in THRESHOLD_SWEEP}

    # Sanity check against the project's own already-trusted numbers: at
    # threshold=0.70 this reimplementation should match
    # eval/results.json's per_field_metrics exactly (same tp/fn/fp, same
    # underlying flags, just recomputed from all_flags_before_floor instead
    # of the pre-filtered `flags` list).
    official = results["per_field_metrics"]
    at_070 = sweep_results[0.70]
    mismatches = []
    for et, official_m in official.items():
        recomputed = at_070.get(et)
        if recomputed is None:
            mismatches.append({"error_type": et, "issue": "missing from recomputed sweep"})
            continue
        if (recomputed["tp"], recomputed["fn"], recomputed["fp"]) != (official_m["tp"], official_m["fn"], official_m["fp"]):
            mismatches.append({
                "error_type": et,
                "official": {"tp": official_m["tp"], "fn": official_m["fn"], "fp": official_m["fp"]},
                "recomputed_at_0.70": {"tp": recomputed["tp"], "fn": recomputed["fn"], "fp": recomputed["fp"]},
            })

    # Flat, dashboard-ready long-format table: one row per (error_type, threshold).
    flat_table = []
    for threshold, per_type in sweep_results.items():
        for et, m in per_type.items():
            flat_table.append({"error_type": et, "threshold": threshold, **m})

    output = {
        "analysis": "threshold_sensitivity",
        "source": "eval/round1_results.json (all_flags_before_floor) matched to eval/results.json's 497-row population",
        "n_rows_used": len(rows),
        "n_rows_skipped_missing_data": skipped,
        "threshold_sweep": THRESHOLD_SWEEP,
        "current_confidence_floor": 0.70,
        "validation_against_official_results_json": {
            "matches": len(mismatches) == 0,
            "mismatches": mismatches,
        },
        "by_threshold": sweep_results,
        "flat_table": flat_table,
    }
    return output


if __name__ == "__main__":
    output = run()
    path = write_json(output, "threshold_sensitivity.json")
    print(f"Threshold-sensitivity analysis written to {path}")
    if output["validation_against_official_results_json"]["matches"]:
        print("Validated: recomputed tp/fn/fp at threshold=0.70 matches eval/results.json's per_field_metrics exactly.")
    else:
        print("WARNING: recomputed numbers at threshold=0.70 do NOT match eval/results.json -- see mismatches below.")
        for m in output["validation_against_official_results_json"]["mismatches"]:
            print(f"  {m}")

    print("\ndrivetrain_swap recall across the threshold sweep:")
    for t in THRESHOLD_SWEEP:
        m = output["by_threshold"][t].get("drivetrain_swap")
        if m:
            print(f"  threshold={t:.2f}  recall={m['recall']}  tp={m['tp']} fn={m['fn']} fp={m['fp']}")
