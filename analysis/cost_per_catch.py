from collections import defaultdict
from analysis.common import load_results, write_json


def _safe_div(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def run() -> dict:
    results = load_results()
    rows = results["rows"]
    per_field_metrics = results["per_field_metrics"]

    per_type_cost = defaultdict(lambda: {"total_cost": 0.0, "caught_cost": 0.0, "missed_cost": 0.0, "n": 0})
    total_cost_all = 0.0
    total_tp_all = 0
    total_fn_cost_all = 0.0

    for r in rows:
        et = r["error_type"]
        cost = r["cost_usd"]["total"]
        per_type_cost[et]["total_cost"] += cost
        per_type_cost[et]["n"] += 1
        total_cost_all += cost
        if r["caught"]:
            per_type_cost[et]["caught_cost"] += cost
        else:
            per_type_cost[et]["missed_cost"] += cost
            total_fn_cost_all += cost

    per_error_type = {}
    for et, c in per_type_cost.items():
        m = per_field_metrics.get(et, {})
        tp, fn, fp = m.get("tp", 0), m.get("fn", 0), m.get("fp", 0)
        total_tp_all += tp
        per_error_type[et] = {
            "n_rows": c["n"],
            "tp": tp,
            "fn": fn,
            "fp": fp,
            "total_cost_usd": round(c["total_cost"], 4),
            "avg_cost_per_listing_usd": _safe_div(c["total_cost"], c["n"]),
            "cost_per_successful_catch_usd": _safe_div(c["total_cost"], tp),
            "cost_of_missed_catches_usd": round(c["missed_cost"], 4),
            "pct_of_type_cost_wasted_on_misses": _safe_div(c["missed_cost"], c["total_cost"]),
            "cost_per_false_positive_usd": _safe_div(c["total_cost"], fp),
            "recall": m.get("recall"),
            "precision": m.get("precision"),
        }

    # Sort by cost-per-catch ascending (most cost-efficient first); None
    # (no catches at all) sorts last.
    ranked = sorted(
        per_error_type.items(),
        key=lambda kv: (kv[1]["cost_per_successful_catch_usd"] is None, kv[1]["cost_per_successful_catch_usd"] or 0),
    )

    overall = {
        "total_pipeline_cost_usd": round(total_cost_all, 4),
        "total_successful_catches": total_tp_all,
        "overall_cost_per_catch_usd": _safe_div(total_cost_all, total_tp_all),
        "total_cost_wasted_on_misses_usd": round(total_fn_cost_all, 4),
        "pct_of_total_cost_wasted_on_misses": _safe_div(total_fn_cost_all, total_cost_all),
        "n_rows": len(rows),
        "avg_cost_per_listing_usd": _safe_div(total_cost_all, len(rows)),
    }

    flat_table = [
        {"error_type": et, **metrics}
        for et, metrics in per_error_type.items()
    ]

    output = {
        "analysis": "cost_per_catch",
        "source": "eval/results.json (rows' cost_usd.total, per_field_metrics)",
        "accounting_assumption": (
            "Each row's full pipeline cost (all checks the verifier runs, not just the one "
            "tested) is attributed to that row's single assigned error_type, mirroring the "
            "eval's one-injected-error-per-listing design. In production a single run's cost "
            "pays for all 9 checks simultaneously -- treat these as eval-design unit costs, "
            "not a general production cost-attribution model."
        ),
        "overall": overall,
        "per_error_type": per_error_type,
        "ranked_most_to_least_cost_efficient": [et for et, _ in ranked],
        "flat_table": flat_table,
    }
    return output


if __name__ == "__main__":
    output = run()
    path = write_json(output, "cost_per_catch.json")
    print(f"Cost-per-catch analysis written to {path}")

    o = output["overall"]
    print(f"\nOverall: ${o['total_pipeline_cost_usd']} total spend across {o['n_rows']} listings "
          f"(avg ${o['avg_cost_per_listing_usd']}/listing)")
    print(f"  {o['total_successful_catches']} real errors successfully caught -> "
          f"${o['overall_cost_per_catch_usd']}/catch overall")
    print(f"  ${o['total_cost_wasted_on_misses_usd']} ({o['pct_of_total_cost_wasted_on_misses']:.1%}) "
          f"spent screening listings whose injected error was never caught")

    print("\nCost per successful catch, by error type (most to least cost-efficient):")
    for et in output["ranked_most_to_least_cost_efficient"]:
        m = output["per_error_type"][et]
        cpc = f"${m['cost_per_successful_catch_usd']}" if m["cost_per_successful_catch_usd"] is not None else "N/A (0 catches)"
        print(f"  {et:20s} {cpc:>12s}/catch   recall={m['recall']}   "
              f"wasted=${m['cost_of_missed_catches_usd']} ({(m['pct_of_type_cost_wasted_on_misses'] or 0):.1%})")
