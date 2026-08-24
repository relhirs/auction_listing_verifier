from analysis import (
    calibration,
    threshold_sensitivity,
    logistic_regression_diagnostic,
    photo_sampling_tradeoff,
    injection_reweighting,
    cost_per_catch,
    bootstrap_ci,
    drivetrain_fix_significance,
    roc_auc,
)
from analysis.common import write_json

MODULES = [
    ("calibration.json", calibration),
    ("threshold_sensitivity.json", threshold_sensitivity),
    ("logistic_regression_diagnostic.json", logistic_regression_diagnostic),
    ("injection_reweighting.json", injection_reweighting),
    ("photo_sampling_tradeoff.json", photo_sampling_tradeoff),
    ("cost_per_catch.json", cost_per_catch),
    ("bootstrap_ci.json", bootstrap_ci),
    ("drivetrain_fix_significance.json", drivetrain_fix_significance),
    ("roc_auc.json", roc_auc),
]


def main():
    for filename, module in MODULES:
        print(f"\n=== Running {module.__name__} ===")
        output = module.run()
        path = write_json(output, filename)
        print(f"  wrote {path}")


if __name__ == "__main__":
    main()
