import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from analysis.common import load_results, write_json

PROSE_PATCHABLE_TYPES = {
    "year_error", "make_error", "engine_error",
    "color_error", "transmission_swap", "drivetrain_swap",
}

REFERENCE_LEVEL = "year_error"  

def _build_dataframe(results: dict) -> tuple[pd.DataFrame, dict]:
    rows = results["rows"]
    mileage_note = None
    mileage_rows_with_patch_data = [
        r for r in rows if r["error_type"] == "mileage_drift" and r.get("prose_patch_applied") is not None
    ]
    if mileage_rows_with_patch_data:
        mileage_note = (
            f"{len(mileage_rows_with_patch_data)} of "
            f"{sum(1 for r in rows if r['error_type'] == 'mileage_drift')} mileage_drift rows in "
            f"eval/results.json carry a non-None prose_patch_applied value, even though the "
            f"current eval/inject_real_errors.py / eval_runner.py code never patches mileage's "
            f"prose -- a stale artifact from an earlier version of that code, not a live "
            f"behavior. mileage_drift is excluded from this regression's predictor set "
            f"regardless, so it doesn't affect the fit, but it's worth knowing the data and "
            f"the current code disagree here."
        )

    usable = [r for r in rows if r["error_type"] in PROSE_PATCHABLE_TYPES]
    excluded_missing_patch_field = [r for r in usable if r.get("prose_patch_applied") is None]
    usable = [r for r in usable if r.get("prose_patch_applied") is not None]

    df = pd.DataFrame([{
        "caught": int(r["caught"]),
        "error_type": r["error_type"],
        "prose_patch_applied": bool(r["prose_patch_applied"]),
        "reassigned": bool(r.get("reassigned", False)),
    } for r in usable])

    notes = {
        "mileage_drift_stale_data_note": mileage_note,
        "n_excluded_non_patchable_types": len(rows) - len(usable) - len(excluded_missing_patch_field),
        "n_excluded_missing_prose_patch_field": len(excluded_missing_patch_field),
        "n_used": len(df),
    }
    return df, notes


def run() -> dict:
    results = load_results()
    df, notes = _build_dataframe(results)

    n_events = int((df["caught"] == 0).sum())  # misses -- the rarer outcome
    n_predictors = 1 + (df["error_type"].nunique() - 1) + 1  # error_type dummies + prose_patch + reassigned
    events_per_predictor = round(n_events / n_predictors, 1) if n_predictors else None

    formula = f"caught ~ C(error_type, Treatment('{REFERENCE_LEVEL}')) + prose_patch_applied + reassigned"
    model = smf.logit(formula, data=df)
    fit_result = model.fit(disp=0)

    conf_int = fit_result.conf_int()
    coefficients = []
    for term in fit_result.params.index:
        coef = fit_result.params[term]
        coefficients.append({
            "term": term,
            "coef": round(float(coef), 4),
            "std_err": round(float(fit_result.bse[term]), 4),
            "z": round(float(fit_result.tvalues[term]), 4),
            "p_value": round(float(fit_result.pvalues[term]), 4),
            "odds_ratio": round(float(np.exp(coef)), 4),
            "odds_ratio_ci_low": round(float(np.exp(conf_int.loc[term, 0])), 4),
            "odds_ratio_ci_high": round(float(np.exp(conf_int.loc[term, 1])), 4),
        })

    output = {
        "analysis": "logistic_regression_diagnostic",
        "purpose": (
            "Inference-only diagnostic on eval/results.json's 497 rows -- tests whether "
            "prose_patch_applied predicts caught after controlling for error_type and "
            "reassigned, i.e. whether the extraction-self-correction mechanism root-caused "
            "for make_error is a live, measurable effect across the other prose-patched "
            "fields. NOT a predictive classifier -- no train/test split, not intended to run "
            "on new listings. See DATA_SCIENCE_DEEP_DIVE.md Part 1 #4."
        ),
        "predictor_types_included": sorted(PROSE_PATCHABLE_TYPES),
        "reference_level": REFERENCE_LEVEL,
        "formula": formula,
        "n_used": notes["n_used"],
        "n_events_misses": n_events,
        "n_predictors": n_predictors,
        "events_per_predictor": events_per_predictor,
        "sample_size_caveat": (
            "Rule of thumb for stable logistic regression is ~10 events per predictor. "
            f"This fit has {events_per_predictor} -- close to that boundary, which is why "
            "the predictor list is deliberately kept to these 3 groups (error_type, "
            "prose_patch_applied, reassigned) rather than adding every available column."
        ),
        "notes": notes,
        "pseudo_r2": round(float(fit_result.prsquared), 4),
        "log_likelihood": round(float(fit_result.llf), 4),
        "converged": bool(fit_result.mle_retvals.get("converged", False)),
        "coefficients": coefficients,
    }
    return output


if __name__ == "__main__":
    output = run()
    path = write_json(output, "logistic_regression_diagnostic.json")
    print(f"Logistic regression diagnostic written to {path}")
    print(f"\nn={output['n_used']}, events (misses)={output['n_events_misses']}, "
          f"events/predictor={output['events_per_predictor']}, converged={output['converged']}")
    if output["notes"]["mileage_drift_stale_data_note"]:
        print(f"\nNOTE: {output['notes']['mileage_drift_stale_data_note']}")
    print("\nCoefficients (odds ratios, reference level = year_error):")
    for c in output["coefficients"]:
        sig = "*" if c["p_value"] < 0.05 else " "
        print(f"  {sig} {c['term']:55s} OR={c['odds_ratio']:<7} "
              f"CI=[{c['odds_ratio_ci_low']}, {c['odds_ratio_ci_high']}]  p={c['p_value']}")
