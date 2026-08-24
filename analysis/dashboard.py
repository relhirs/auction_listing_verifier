import json
from pathlib import Path

import pandas as pd
import streamlit as st

OUTPUT_DIR = Path(__file__).parent / "output"

st.set_page_config(
    page_title="Listing Checker -- Analysis Dashboard",
    page_icon="📊",
    layout="wide",
)


# --- Shared loader -----------------------------------------------------
def load(name: str) -> dict:
    """Reads analysis/output/<name>.json. Stops the whole app with a clear
    message if the file is missing, instead of crashing with a raw
    FileNotFoundError -- the file only won't exist if run_all.py hasn't
    been run yet, so the fix is always the same one command."""
    path = OUTPUT_DIR / f"{name}.json"
    if not path.exists():
        st.error(
            f"'{name}.json' not found in analysis/output/. "
            f"Run `python -m analysis.run_all` from the project root first, "
            f"then reload this page."
        )
        st.stop()
    with open(path) as f:
        return json.load(f)


# --- Page: Overview ------------------------------------------------------
def page_overview():
    st.title("📊 Listing Checker — Analysis Dashboard")
    st.caption(
        "Companion to DATA_SCIENCE_RESULTS.md — 9 of its 10 analyses are live here "
        "(section 5, keyword attribution, was removed from the codebase — see its "
        "note there), browsable "
        "instead of read top to bottom. Pick a page from the sidebar."
    )

    reweighting = load("injection_reweighting")
    cost = load("cost_per_catch")
    calibration = load("calibration")

    st.subheader("Headline numbers")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Overall verdict accuracy",
        reweighting["validation_against_official_results_json"]["official_verdict_accuracy"],
    )
    col2.metric("Overall cost per catch", f"${cost['overall']['overall_cost_per_catch_usd']}")
    col3.metric(
        "% of spend wasted on misses",
        f"{cost['overall']['pct_of_total_cost_wasted_on_misses']:.1%}",
    )
    col4.metric("Overall Brier score (calibration)", calibration["overall"]["brier_score"])

    st.subheader("The cross-cutting finding")
    st.markdown(
        "Four of the seven analyses independently converged on the same weak "
        "spot — **`drivetrain_swap`**, recall stuck at 0.65 — well before any "
        "code changed. That convergence (calibration, threshold-sensitivity, "
        "logistic regression, and cost-per-catch all pointing the same way) is "
        "what made it the clear next thing to fix. Section 9 of "
        "DATA_SCIENCE_RESULTS.md documents the fix: two separate bugs (a stale "
        "test-data file, plus a genuine extraction self-correction bug matching "
        "`make_error`'s known mechanism), both fixed. **Recall is now 1.0 "
        "(20/20), zero spend wasted on misses** — it's still the single most "
        "expensive check per catch ($0.47), but now because drivetrain "
        "listings just cost more to run through photo vision, not because of "
        "missed detections."
    )

    st.subheader("Pages")
    st.markdown(
        "- **1. Calibration** — does each check's stated confidence match reality?\n"
        "- **2. Threshold Sensitivity** — what happens if the confidence floor moves?\n"
        "- **3. Logistic Regression** — what actually predicts whether an error gets caught?\n"
        "- **4. Injection Reweighting** — is the headline accuracy number an artifact of the test mix?\n"
        "- *(section 5, Keyword Attribution, was removed from the codebase and this "
        "dashboard — its write-up is kept in DATA_SCIENCE_RESULTS.md as a historical "
        "record, not regenerated)*\n"
        "- **6. Photo Sampling** — how many photos does detection actually need?\n"
        "- **7. Cost Per Catch** — what does it cost, in real dollars, to catch one error?\n"
        "- **8. Bootstrap CI** — how much should you trust the headline accuracy number?\n"
        "- **9. Drivetrain Fix Significance** — was the recall jump a real effect, or noise?\n"
        "- **10. ROC / AUC** — is each check's confidence signal actually a useful ranking, threshold aside?"
    )


# --- Page: Calibration -----------------------------------------------------
def page_calibration():
    st.title("1. Confidence Calibration")
    st.caption(
        "Does each check's stated confidence match how often it's actually "
        "correct? See DATA_SCIENCE_RESULTS.md section 1 for the full explanation."
    )
    data = load("calibration")

    st.metric("Overall Brier score (lower is better)", data["overall"]["brier_score"])

    st.subheader("Brier score by check")
    brier_by_field = {field: d["brier_score"] for field, d in data["per_field_name"].items()}
    st.bar_chart(pd.Series(brier_by_field, name="brier_score"))

    st.subheader("Full table: every confidence value each check produces")
    df = pd.DataFrame(data["flat_table"])
    st.markdown(
        "`field_name` = every time this **check** fired, regardless of what was "
        "actually planted on the listing. `error_type` = only listings where this "
        "**specific error was actually planted**, every flag that fired there. "
        "Same underlying flags, two different GROUP BYs — so the same check/type "
        "can show a different `n` and `observed_correct_rate` under each one. "
        "See DATA_SCIENCE_RESULTS.md section 1 for a full worked example (drivetrain)."
    )
    field_filter = st.selectbox(
        "Filter by group type", options=sorted(df["group_type"].unique()), index=0
    )
    st.dataframe(df[df["group_type"] == field_filter], use_container_width=True)


# --- Page: Threshold sensitivity -------------------------------------------
def page_threshold_sensitivity():
    st.title("2. Threshold Sensitivity")
    st.caption(
        "What would recall look like at a different CONFIDENCE_FLOOR setting? "
        "See DATA_SCIENCE_RESULTS.md section 2."
    )
    data = load("threshold_sensitivity")

    st.subheader("Recall by error type, across the threshold sweep")
    df = pd.DataFrame(data["flat_table"])
    pivot = df.pivot(index="threshold", columns="error_type", values="recall")
    st.line_chart(pivot)
    st.caption(
        "drivetrain_swap is now flat at 1.0 recall across almost the whole "
        "range (it drops to 0 only at threshold=0.95, since the check's flat "
        "0.9 confidence value sits below that cutoff by construction) -- "
        "before the section 9 fix, it was flat at 0.65 instead, for a "
        "genuinely different reason: those flags never fired at all, at any "
        "confidence level, so no threshold setting could have recovered them."
    )

    st.subheader("Full table")
    st.dataframe(df, use_container_width=True)


# --- Page: Logistic regression ----------------------------------------------
def page_logistic_regression():
    st.title("3. Logistic Regression Diagnostic")
    st.caption(
        "What predicts whether a planted error actually gets caught? "
        "See DATA_SCIENCE_RESULTS.md section 3."
    )
    data = load("logistic_regression_diagnostic")

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows used", data["n_used"])
    col2.metric("Misses (events)", data["n_events_misses"])
    col3.metric("Events per predictor", data["events_per_predictor"])

    st.subheader("Odds ratio per factor")
    df = pd.DataFrame(data["coefficients"])
    chart_df = df.set_index("term")["odds_ratio"]
    st.bar_chart(chart_df)
    st.caption("Above 1.0 = higher odds of being caught. Below 1.0 = lower odds.")

    st.subheader("Full coefficient table (odds ratio, confidence interval, p-value)")
    st.dataframe(df, use_container_width=True)


# --- Page: Injection reweighting --------------------------------------------
def page_injection_reweighting():
    st.title("4. Injection-Ratio Reweighting")
    st.caption(
        "Is the headline accuracy propped up by the test data's uneven "
        "error-type mix? See DATA_SCIENCE_RESULTS.md section 4."
    )
    data = load("injection_reweighting")

    st.subheader("Mean recall / verdict accuracy under 3 different weightings")
    rows = {
        scheme: {"mean_recall": d["mean_recall"], "mean_verdict_accuracy": d["mean_verdict_accuracy"]}
        for scheme, d in data["weighting_schemes"].items()
    }
    st.bar_chart(pd.DataFrame(rows).T)

    st.subheader("Full table (by error type and weighting scheme)")
    st.dataframe(pd.DataFrame(data["flat_table"]), use_container_width=True)


# --- Page: Photo sampling ---------------------------------------------------
def page_photo_sampling():
    st.title("6. Photo-Sampling Cost/Recall Tradeoff")
    st.caption(
        "How many photos does each check actually need? "
        "See DATA_SCIENCE_RESULTS.md section 6."
    )
    data = load("photo_sampling_tradeoff")

    st.subheader("Recall vs. sample size (k), by check")
    df = pd.DataFrame(data["flat_table"])
    df["k_str"] = df["k"].astype(str)
    pivot = df.pivot(index="k_str", columns="error_type", values="mean_recall")
    # Keep k in the intended numeric-then-"full" order, not alphabetical.
    order = [str(k) for k in data["k_values"]]
    pivot = pivot.reindex(order)
    st.line_chart(pivot)

    st.subheader("Full table")
    st.dataframe(df, use_container_width=True)


# --- Page: Cost per catch ---------------------------------------------------
def page_cost_per_catch():
    st.title("7. Cost Per Catch")
    st.caption(
        "What does it cost, in real dollars, to catch one real error? "
        "See DATA_SCIENCE_RESULTS.md section 7."
    )
    data = load("cost_per_catch")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total pipeline spend", f"${data['overall']['total_pipeline_cost_usd']}")
    col2.metric("Overall cost per catch", f"${data['overall']['overall_cost_per_catch_usd']}")
    col3.metric(
        "Wasted on misses",
        f"${data['overall']['total_cost_wasted_on_misses_usd']} "
        f"({data['overall']['pct_of_total_cost_wasted_on_misses']:.1%})",
    )

    st.subheader("Cost per successful catch, by error type")
    df = pd.DataFrame(data["flat_table"]).set_index("error_type")
    df = df.loc[data["ranked_most_to_least_cost_efficient"]]
    st.bar_chart(df["cost_per_successful_catch_usd"])
    st.caption(
        "drivetrain_swap is still the priciest check per catch, by a wide "
        "margin -- but as of the section 9 fix, 0% of that spend is wasted "
        "(same as make_error/mileage_drift). It costs more per catch because "
        "drivetrain listings are pricier to run through photo vision, not "
        "because of missed detections."
    )

    st.subheader("Full table")
    st.dataframe(df, use_container_width=True)


# --- Page: Bootstrap confidence intervals -----------------------------------
def page_bootstrap_ci():
    st.title("8. Bootstrap Confidence Intervals")
    st.caption(
        "How much should you trust the headline accuracy number? "
        "See DATA_SCIENCE_RESULTS.md section 10."
    )
    data = load("bootstrap_ci")

    overall = data["overall_verdict_accuracy"]
    st.metric(
        "Overall verdict accuracy",
        overall["point_estimate"],
        help=f"95% CI: [{overall['ci_low']}, {overall['ci_high']}]  (se={overall['bootstrap_se']})",
    )
    st.caption(f"95% CI: [{overall['ci_low']}, {overall['ci_high']}]  --  se={overall['bootstrap_se']}  "
               f"--  {overall['n_iterations']} bootstrap resamples, n={overall['n']} rows")

    st.subheader("Recall per error type, with 95% CI")
    df = pd.DataFrame(data["per_error_type_recall"]).T
    df.index.name = "error_type"
    st.bar_chart(df["point_estimate"])
    st.caption(
        "Bar height is the point estimate; see the full table below for each "
        "type's actual CI bounds -- a bar chart alone can't show error bars "
        "with Streamlit's built-in chart types."
    )
    st.dataframe(df[["point_estimate", "ci_low", "ci_high", "bootstrap_se", "n"]], use_container_width=True)


# --- Page: Drivetrain fix significance test ---------------------------------
def page_drivetrain_fix_significance():
    st.title("9. Drivetrain Fix Significance Test")
    st.caption(
        "Was the drivetrain_swap recall jump (0.65 -> 1.0) a real effect, "
        "or could it happen by chance at n=20? See DATA_SCIENCE_RESULTS.md section 11."
    )
    data = load("drivetrain_fix_significance")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Before (recall)", data["before"]["recall"], f"{data['before']['caught']}/{data['before']['n']} caught")
    with col2:
        st.metric("After (recall)", data["after"]["recall"], f"{data['after']['caught']}/{data['after']['n']} caught")

    st.subheader("McNemar's exact test (paired)")
    st.caption(
        "Paired, not independent samples: the same 20 auctions were measured "
        "before and after the fix, so McNemar's test is used instead of "
        "Fisher's exact test (which would assume two independent groups)."
    )
    col3, col4 = st.columns(2)
    col3.metric("p-value", data["p_value"])
    col4.metric("Significant at 0.05?", "Yes" if data["significant_at_0.05"] else "No")
    st.caption(data["note"])

    st.subheader("Paired breakdown")
    pb = data["paired_breakdown"]
    st.write(
        f"Caught both times: **{pb['both_caught']}** &nbsp;|&nbsp; "
        f"Missed → caught: **{pb['fixed_missed_to_caught']}** &nbsp;|&nbsp; "
        f"Caught → missed: **{pb['broke_caught_to_missed']}** &nbsp;|&nbsp; "
        f"Missed both times: **{pb['both_missed']}**"
    )

    st.subheader("Contingency table (caught / missed)")
    table_df = pd.DataFrame(
        data["contingency_table"], index=["before", "after"], columns=["caught", "missed"]
    )
    st.dataframe(table_df, use_container_width=True)


# --- Page: ROC / AUC per check -----------------------------------------------
def page_roc_auc():
    st.title("10. ROC / AUC Per Check")
    st.caption(
        "A threshold-independent evaluation metric for each check's confidence signal. "
        "See DATA_SCIENCE_RESULTS.md section 12."
    )
    data = load("roc_auc")

    st.subheader("AUC by check")
    df = pd.DataFrame(data["flat_table"]).set_index("field_name")
    st.bar_chart(df["auc"])
    st.caption(
        "0.5 = no better than a coin flip at ranking real errors above non-errors; "
        "1.0 = perfect ranking. Checks flagged low_resolution or "
        "few_positive_examples below have an AUC that's a rough estimate, not a "
        "precise one -- see the full table."
    )

    st.subheader("ROC curve for one check")
    field_name = st.selectbox("Choose a check", options=sorted(data["per_check"].keys()))
    curve = data["per_check"][field_name]
    if curve["auc"] is None:
        st.warning("AUC undefined for this check -- no positive or no negative examples.")
    else:
        curve_df = pd.DataFrame({"fpr": curve["fpr"], "tpr": curve["tpr"], "chance": curve["fpr"]}).set_index("fpr")
        st.line_chart(curve_df)
        flags = []
        if curve["low_resolution"]:
            flags.append("low-resolution (few distinct confidence values)")
        if curve["few_positive_examples"]:
            flags.append("few positive examples")
        flag_str = f" ({', '.join(flags)})" if flags else ""
        st.caption(f"AUC = {curve['auc']}{flag_str}  --  n_positive={curve['n_positive']}, "
                   f"n_negative={curve['n_negative']}. 'chance' is the diagonal reference line "
                   "a random, uninformative score would produce.")

    st.subheader("Full table")
    st.dataframe(df, use_container_width=True)


# --- Sidebar navigation ------------------------------------------------
PAGES = {
    "Overview": page_overview,
    "1. Calibration": page_calibration,
    "2. Threshold Sensitivity": page_threshold_sensitivity,
    "3. Logistic Regression": page_logistic_regression,
    "4. Injection Reweighting": page_injection_reweighting,
    "6. Photo Sampling": page_photo_sampling,
    "7. Cost Per Catch": page_cost_per_catch,
    "8. Bootstrap CI": page_bootstrap_ci,
    "9. Drivetrain Fix Significance": page_drivetrain_fix_significance,
    "10. ROC / AUC": page_roc_auc,
}

st.sidebar.title("Navigation")
selected = st.sidebar.radio("Go to", list(PAGES.keys()))
PAGES[selected]()
