from collections import defaultdict

from analysis.common import load_results, bootstrap_ci, write_json

N_ITERATIONS = 5000
SEED = 0


def run() -> dict:
    results = load_results()
    rows = results["rows"]

    overall_verdict_matches = [1 if r["verdict_match"] else 0 for r in rows]
    overall_ci = bootstrap_ci(overall_verdict_matches, n_iterations=N_ITERATIONS, seed=SEED)

    caught_by_type = defaultdict(list)
    for r in rows:
        caught_by_type[r["error_type"]].append(1 if r["caught"] else 0)

    per_error_type_recall_ci = {
        et: bootstrap_ci(values, n_iterations=N_ITERATIONS, seed=SEED)
        for et, values in sorted(caught_by_type.items())
    }

    flat_table = [
        {"metric": "verdict_accuracy", "group": "overall", **overall_ci}
    ] + [
        {"metric": "recall", "group": et, **ci}
        for et, ci in per_error_type_recall_ci.items()
    ]

    output = {
        "analysis": "bootstrap_confidence_intervals",
        "source": "eval/results.json (rows)",
        "method": (
            "Percentile bootstrap: resample n rows with replacement, "
            f"{N_ITERATIONS} times, take the 2.5th/97.5th percentile of the "
            "resulting statistic distribution as the 95% CI. seed=0 for "
            "reproducibility."
        ),
        "overall_verdict_accuracy": overall_ci,
        "per_error_type_recall": per_error_type_recall_ci,
        "flat_table": flat_table,
    }
    return output


if __name__ == "__main__":
    output = run()
    path = write_json(output, "bootstrap_ci.json")
    print(f"Bootstrap confidence intervals written to {path}")
    o = output["overall_verdict_accuracy"]
    print(f"\nOverall verdict accuracy: {o['point_estimate']} "
          f"(95% CI: [{o['ci_low']}, {o['ci_high']}], se={o['bootstrap_se']})")
    print("\nPer-error-type recall, with 95% CI:")
    for et, ci in output["per_error_type_recall"].items():
        print(f"  {et:20s} {ci['point_estimate']:.4f}  "
              f"[{ci['ci_low']:.4f}, {ci['ci_high']:.4f}]  (n={ci['n']})")
