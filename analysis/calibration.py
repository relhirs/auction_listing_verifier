from collections import defaultdict
from typing import Optional

from analysis.common import (
    load_results, load_matched_round1, build_row_records,
    flatten_flag_observations, write_json,
)


def _bin_stats(observations: list[dict]) -> list[dict]:
    """Groups by exact confidence value; Brier-relevant stats per group."""
    by_conf = defaultdict(list)
    for obs in observations:
        by_conf[obs["confidence"]].append(obs["label"])

    bins = []
    for conf in sorted(by_conf):
        labels = by_conf[conf]
        n = len(labels)
        observed_rate = sum(labels) / n
        bins.append({
            "confidence": conf,
            "n": n,
            "observed_correct_rate": round(observed_rate, 4),
            "gap": round(observed_rate - conf, 4),  # positive = underconfident, negative = overconfident
            "brier_contribution": round(sum((conf - l) ** 2 for l in labels) / n, 4),
        })
    return bins


def _brier_score(observations: list[dict]) -> Optional[float]:
    if not observations:
        return None
    return round(sum((o["confidence"] - o["label"]) ** 2 for o in observations) / len(observations), 4)


def run() -> dict:
    results = load_results()
    matched_round1 = load_matched_round1(results)
    rows, skipped = build_row_records(matched_round1)
    observations = flatten_flag_observations(rows)

    overall_bins = _bin_stats(observations)
    overall_brier = _brier_score(observations)

    # Per field_name (i.e. per check) -- the more actionable cut, since
    # confidence is a per-check constant, not a per-flag draw.
    by_field = defaultdict(list)
    for obs in observations:
        by_field[obs["field_name"]].append(obs)
    per_field = {
        field: {
            "bins": _bin_stats(obs_list),
            "brier_score": _brier_score(obs_list),
            "n": len(obs_list),
        }
        for field, obs_list in sorted(by_field.items())
    }

    # Per severity tier
    by_severity = defaultdict(list)
    for obs in observations:
        by_severity[obs["severity"]].append(obs)
    per_severity = {
        sev: {
            "bins": _bin_stats(obs_list),
            "brier_score": _brier_score(obs_list),
            "n": len(obs_list),
        }
        for sev, obs_list in sorted(by_severity.items())
    }

    # Per error_type (the row's ground-truth type, not the flag's own field)
    by_error_type = defaultdict(list)
    for obs in observations:
        by_error_type[obs["error_type"]].append(obs)
    per_error_type = {
        et: {
            "bins": _bin_stats(obs_list),
            "brier_score": _brier_score(obs_list),
            "n": len(obs_list),
        }
        for et, obs_list in sorted(by_error_type.items())
    }

    # Flat, dashboard-ready long-format table: one row per (group_type,
    # group_value, confidence) triple.
    flat_table = []
    for b in overall_bins:
        flat_table.append({"group_type": "overall", "group_value": "overall", **b})
    for field, d in per_field.items():
        for b in d["bins"]:
            flat_table.append({"group_type": "field_name", "group_value": field, **b})
    for sev, d in per_severity.items():
        for b in d["bins"]:
            flat_table.append({"group_type": "severity", "group_value": sev, **b})
    for et, d in per_error_type.items():
        for b in d["bins"]:
            flat_table.append({"group_type": "error_type", "group_value": et, **b})

    output = {
        "analysis": "confidence_calibration",
        "source": "eval/round1_results.json (all_flags_before_floor) matched to eval/results.json's 497-row population",
        "n_rows_used": len(rows),
        "n_rows_skipped_missing_data": skipped,
        "n_flags_total": len(observations),
        "confidence_floor_currently_in_use": 0.70,
        "note": (
            "Confidence values in this codebase are fixed per-check constants "
            "(9 distinct values used across core/verifier.py), not a continuous "
            "model output -- grouping is by exact value, not arbitrary bins. "
            "gap = observed_correct_rate - confidence: positive means the check "
            "is underconfident (better than it claims), negative means "
            "overconfident (worse than it claims, the riskier direction)."
        ),
        "overall": {"bins": overall_bins, "brier_score": overall_brier},
        "per_field_name": per_field,
        "per_severity": per_severity,
        "per_error_type": per_error_type,
        "flat_table": flat_table,
    }
    return output


if __name__ == "__main__":
    output = run()
    path = write_json(output, "calibration.json")
    print(f"Confidence calibration analysis written to {path}")
    print(f"\nOverall Brier score: {output['overall']['brier_score']} (n={output['n_flags_total']} flags)")
    print("\nPer-check (field_name) calibration:")
    for field, d in sorted(output["per_field_name"].items()):
        print(f"{field:25s} brier={d['brier_score']}  n={d['n']}")
        for b in d["bins"]:
            print(f"confidence={b['confidence']:<5} n={b['n']:<4} observed={b['observed_correct_rate']:<6} gap={b['gap']:+.3f}")
