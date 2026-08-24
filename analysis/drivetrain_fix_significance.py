import json

from statsmodels.stats.contingency_tables import mcnemar

from analysis.common import EVAL_DIR, load_results, write_json

PRE_FIX_BACKUP_PATH = EVAL_DIR / "results_PRE_DRIVETRAIN_FIX_backup.json"
ERROR_TYPE = "drivetrain_swap"


def _load_pre_fix_results() -> dict:
    if not PRE_FIX_BACKUP_PATH.exists():
        raise FileNotFoundError(
            f"{PRE_FIX_BACKUP_PATH} not found -- this analysis compares against "
            "that specific pre-fix snapshot and cannot substitute a different "
            "file or an estimated number. See this module's docstring."
        )
    with open(PRE_FIX_BACKUP_PATH) as f:
        return json.load(f)


def _caught_map(results: dict, error_type: str) -> dict[str, bool]:
    return {
        r["auction_id"]: r["caught"]
        for r in results["rows"] if r["error_type"] == error_type
    }


def run() -> dict:
    pre_fix = _load_pre_fix_results()
    post_fix = load_results()

    pre_map = _caught_map(pre_fix, ERROR_TYPE)
    post_map = _caught_map(post_fix, ERROR_TYPE)

    pre_ids = set(pre_map)
    post_ids = set(post_map)
    if pre_ids != post_ids:
        raise ValueError(
            "Pre-fix and post-fix drivetrain_swap auction_id sets differ -- "
            "this analysis assumes the same 20 auctions measured twice "
            f"(paired data). Only in pre: {pre_ids - post_ids}. "
            f"Only in post: {post_ids - pre_ids}."
        )

    both_caught = both_missed = fixed = broke = 0
    for aid in pre_ids:
        before, after = pre_map[aid], post_map[aid]
        if before and after:
            both_caught += 1
        elif not before and not after:
            both_missed += 1
        elif not before and after:
            fixed += 1
        else:
            broke += 1

    n = len(pre_ids)
    caught_before = both_caught + broke
    caught_after = both_caught + fixed

    # McNemar's 2x2 table: [[both_caught, caught_before_only], [caught_after_only, both_missed]]
    table = [[both_caught, broke], [fixed, both_missed]]
    result = mcnemar(table, exact=True)

    output = {
        "analysis": "drivetrain_fix_significance_test",
        "source": (
            "eval/results_PRE_DRIVETRAIN_FIX_backup.json (before) vs. "
            "eval/results.json (after), same 20 auction_ids in both"
        ),
        "error_type": ERROR_TYPE,
        "method": "McNemar's exact test, paired (statsmodels.stats.contingency_tables.mcnemar, exact=True)",
        "method_note": (
            "This is paired data (the same 20 auctions, measured before and "
            "after the fix), not two independent samples -- an earlier "
            "version of this analysis used Fisher's exact test, which "
            "assumes independent samples and was a methodological error. "
            "McNemar's test uses only the discordant pairs (cases that "
            "flipped state) and ignores concordant pairs (caught both times "
            "or missed both times), which carry no information about a "
            "systematic shift."
        ),
        "before": {"n": n, "caught": caught_before, "missed": n - caught_before,
                    "recall": round(caught_before / n, 4)},
        "after": {"n": n, "caught": caught_after, "missed": n - caught_after,
                   "recall": round(caught_after / n, 4)},
        "paired_breakdown": {
            "both_caught": both_caught,
            "both_missed": both_missed,
            "fixed_missed_to_caught": fixed,
            "broke_caught_to_missed": broke,
        },
        "contingency_table": table,
        "statistic": round(float(result.statistic), 4),
        "p_value": round(float(result.pvalue), 6),
        "significant_at_0.05": bool(result.pvalue < 0.05),
        "note": (
            "Small-sample caveat: only 7 of 20 pairs are discordant, which "
            "limits statistical power. A non-significant result here would "
            "not contradict the fix -- the root cause was independently "
            "confirmed by tracing every real miss to its exact mechanism in "
            "the code (see DATA_SCIENCE_RESULTS.md section 9), not inferred "
            "from this test alone. This test is corroborating evidence, not "
            "the primary proof."
        ),
    }
    return output


if __name__ == "__main__":
    output = run()
    path = write_json(output, "drivetrain_fix_significance.json")
    print(f"Drivetrain fix significance test written to {path}")
    b, a = output["before"], output["after"]
    print(f"\nBefore: {b['caught']}/{b['n']} caught (recall={b['recall']})")
    print(f"After:  {a['caught']}/{a['n']} caught (recall={a['recall']})")
    pb = output["paired_breakdown"]
    print(f"\nPaired breakdown: both_caught={pb['both_caught']}, "
          f"fixed={pb['fixed_missed_to_caught']}, broke={pb['broke_caught_to_missed']}, "
          f"both_missed={pb['both_missed']}")
    print(f"\nMcNemar's exact test: statistic={output['statistic']}, "
          f"p={output['p_value']} "
          f"({'significant' if output['significant_at_0.05'] else 'NOT significant'} at 0.05)")
