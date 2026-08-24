import sqlite3
from collections import defaultdict
from typing import Optional

from corpus.config import DB_PATH
from analysis.common import load_results, write_json

# core/verifier.py has no listing-vs-VIN spec check that distinguishes
# "which spec field" the community's VIN_SPEC_MISMATCH category refers to
# -- it's one bucket covering year/make/engine/transmission/drivetrain/color
# mismatches together. Splitting its weight evenly across the 6
# corresponding injected error types is the best approximation the two
# taxonomies support; stated as an approximation, not a measured split.
VIN_SPEC_MISMATCH_FAMILY = [
    "year_error", "make_error", "engine_error",
    "transmission_swap", "drivetrain_swap", "color_error",
]
DIRECT_MAPPING = {
    "ODOMETER_DISCREPANCY": "mileage_drift",
    "DUPLICATE_PHOTO": "duplicate_photo",
    "MISSING_PHOTO_ANGLE": "missing_angle",
}
# UNDISCLOSED_DAMAGE and OTHER have no analog among the 9 injected error
# types at all (there is no injector, and no verifier check, for
# undisclosed damage -- see PROJECT_DEEP_DIVE.md / DATA_SCIENCE_DEEP_DIVE.md's
# note on core/verifier.py's damage counters being display-only). Excluded
# from the real-world weighting and the excluded share is reported
# explicitly rather than silently redistributed.
UNMAPPABLE_CATEGORIES = {"UNDISCLOSED_DAMAGE", "OTHER"}

ALL_ERROR_TYPES = [
    "year_error", "make_error", "mileage_drift", "transmission_swap",
    "drivetrain_swap", "engine_error", "color_error", "duplicate_photo",
    "missing_angle",
]


def _real_world_category_counts() -> dict:
    """Sourced from corpus.db's verified_community_errors table -- 25
    manually human-reviewed, confirmed-real discrepancies (a curated
    subset/superset of what comment_mining_agent.py's LLM classifier
    flagged as candidates in mined_discrepancies), not the raw LLM
    classifications. mined_flag_category is the category label (same
    taxonomy as mined_discrepancies.flag_category). One row has no
    auction_id at all (a general note, not tied to a specific listing) and
    is excluded -- it can't be attributed to any of the 9 injected error
    types the weighting model needs a specific auction for."""
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT mined_flag_category, COUNT(*) FROM verified_community_errors "
            "WHERE auction_id IS NOT NULL AND mined_flag_category IS NOT NULL "
            "GROUP BY mined_flag_category"
        ).fetchall()
    finally:
        conn.close()
    return dict(rows)


def _real_world_weights(category_counts: dict) -> tuple[dict, dict]:
    mappable_total = sum(n for cat, n in category_counts.items() if cat not in UNMAPPABLE_CATEGORIES)
    unmappable_total = sum(n for cat, n in category_counts.items() if cat in UNMAPPABLE_CATEGORIES)
    grand_total = sum(category_counts.values())

    weights = defaultdict(float)
    vin_spec_n = category_counts.get("VIN_SPEC_MISMATCH", 0)
    vin_spec_share = vin_spec_n / mappable_total
    for et in VIN_SPEC_MISMATCH_FAMILY:
        weights[et] = vin_spec_share / len(VIN_SPEC_MISMATCH_FAMILY)
    for cat, et in DIRECT_MAPPING.items():
        weights[et] = category_counts.get(cat, 0) / mappable_total

    metadata = {
        "real_world_category_counts": category_counts,
        "grand_total_confirmed_discrepancies": grand_total,
        "excluded_unmappable_categories": sorted(UNMAPPABLE_CATEGORIES),
        "excluded_unmappable_count": unmappable_total,
        "excluded_unmappable_share_of_all_confirmed": round(unmappable_total / grand_total, 4),
        "mappable_total_used_for_renormalization": mappable_total,
        "note": (
            "UNDISCLOSED_DAMAGE and OTHER together are "
            f"{unmappable_total}/{grand_total} ({unmappable_total/grand_total:.1%}) of all "
            "real, community-confirmed discrepancies, and have no corresponding injected "
            "error type or verifier check at all -- excluded from this weighting and "
            "reported here rather than silently redistributed onto categories that do exist. "
            "VIN_SPEC_MISMATCH is a single real-world bucket covering 6 of this project's 9 "
            "injected error types together; its weight is split evenly across them as the "
            "closest approximation the two taxonomies support, not a measured sub-split."
        ),
    }
    return dict(weights), metadata


def _safe_round(value: Optional[float], ndigits: int) -> Optional[float]:
    return round(value, ndigits) if value is not None else None


def _weighted_mean(values_by_type: dict, weights: dict) -> Optional[float]:
    applicable = {et: w for et, w in weights.items() if et in values_by_type and values_by_type[et] is not None}
    total_weight = sum(applicable.values())
    if total_weight == 0:
        return None
    return sum(values_by_type[et] * w for et, w in applicable.items()) / total_weight


def run() -> dict:
    results = load_results()
    rows = results["rows"]
    per_field_metrics = results["per_field_metrics"]

    n_by_type = defaultdict(int)
    verdict_match_by_type = defaultdict(list)
    for r in rows:
        n_by_type[r["error_type"]] += 1
        verdict_match_by_type[r["error_type"]].append(1 if r["verdict_match"] else 0)

    n_total = sum(n_by_type.values())
    recall_by_type = {et: per_field_metrics[et]["recall"] for et in ALL_ERROR_TYPES if et in per_field_metrics}
    verdict_accuracy_by_type = {
        et: sum(vals) / len(vals) for et, vals in verdict_match_by_type.items()
    }

    weight_schemes = {
        "current_realized": {et: n_by_type.get(et, 0) / n_total for et in ALL_ERROR_TYPES},
        "uniform": {et: 1 / len(ALL_ERROR_TYPES) for et in ALL_ERROR_TYPES},
    }
    real_world_category_counts = _real_world_category_counts()
    real_world_weights, real_world_metadata = _real_world_weights(real_world_category_counts)
    weight_schemes["real_world_informed"] = real_world_weights

    reweighted = {}
    for scheme_name, weights in weight_schemes.items():
        reweighted[scheme_name] = {
            "weights_by_error_type": {et: round(weights.get(et, 0.0), 4) for et in ALL_ERROR_TYPES},
            "mean_recall": _safe_round(_weighted_mean(recall_by_type, weights), 4),
            "mean_verdict_accuracy": _safe_round(_weighted_mean(verdict_accuracy_by_type, weights), 4),
        }

    # Correctness check: current_realized weighting should reproduce the
    # official headline verdict_accuracy exactly.
    official_verdict_accuracy = results["verdict_accuracy"]
    recomputed = reweighted["current_realized"]["mean_verdict_accuracy"]
    validation = {
        "official_verdict_accuracy": official_verdict_accuracy,
        "recomputed_under_current_realized_weights": recomputed,
        "matches": abs(official_verdict_accuracy - recomputed) < 0.001,
    }

    # Flat, dashboard-ready long-format table.
    flat_table = []
    for scheme_name, data in reweighted.items():
        for et in ALL_ERROR_TYPES:
            flat_table.append({
                "weighting_scheme": scheme_name,
                "error_type": et,
                "weight": data["weights_by_error_type"].get(et, 0.0),
                "recall": recall_by_type.get(et),
                "verdict_accuracy": _safe_round(verdict_accuracy_by_type.get(et), 4),
                "n_rows": n_by_type.get(et, 0),
            })

    output = {
        "analysis": "injection_ratio_reweighting",
        "source": "eval/results.json (per_field_metrics, rows) + corpus/corpus.db (verified_community_errors)",
        "n_rows_total": n_total,
        "n_by_error_type": dict(n_by_type),
        "per_error_type_recall": recall_by_type,
        "per_error_type_verdict_accuracy": {k: round(v, 4) for k, v in verdict_accuracy_by_type.items()},
        "weighting_schemes": reweighted,
        "real_world_weighting_metadata": real_world_metadata,
        "validation_against_official_results_json": validation,
        "flat_table": flat_table,
    }
    return output


if __name__ == "__main__":
    output = run()
    path = write_json(output, "injection_reweighting.json")
    print(f"Injection-ratio reweighting analysis written to {path}")
    if output["validation_against_official_results_json"]["matches"]:
        print("Validated: current_realized-weighted verdict accuracy matches eval/results.json's "
              f"official verdict_accuracy ({output['validation_against_official_results_json']['official_verdict_accuracy']}).")
    else:
        print("WARNING: current_realized-weighted verdict accuracy does NOT match the official number -- "
              f"{output['validation_against_official_results_json']}")

    print("\nMean recall and verdict accuracy under each weighting scheme:")
    for scheme, data in output["weighting_schemes"].items():
        print(f"  {scheme:22s} mean_recall={data['mean_recall']}  mean_verdict_accuracy={data['mean_verdict_accuracy']}")

    print(f"\n{output['real_world_weighting_metadata']['note']}")
