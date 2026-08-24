// Source: analysis/output/calibration.json (overall, per_field_name),
// analysis/output/confidence_scaling_validation.json (smoothing before/after).
// Brier score: lower is better, 0 is a perfectly calibrated check.

export const OVERALL_BRIER = { score: 0.0855, n: 500, totalFlags: 1669 }

export const BRIER_BY_FIELD = [
  { field: 'make', label: 'Make', brier: 0.0001, n: 52, status: 'well_calibrated' },
  { field: 'duplicate_photos', label: 'Duplicate photo', brier: 0.0025, n: 284, status: 'well_calibrated' },
  { field: 'mileage', label: 'Mileage', brier: 0.0223, n: 34, status: 'well_calibrated' },
  { field: 'photo_angles', label: 'Missing angle', brier: 0.0134, n: 486, status: 'well_calibrated' },
  { field: 'transmission', label: 'Transmission', brier: 0.1338, n: 32, status: 'ok' },
  { field: 'engine_displacement', label: 'Engine displacement', brier: 0.158, n: 140, status: 'ok' },
  { field: 'year', label: 'Year', brier: 0.0924, n: 188, status: 'ok' },
  { field: 'drivetrain', label: 'Drivetrain', brier: 0.164, n: 344, status: 'ok', note: 'Was 0.174 and flagged overconfident before the 2026-08-23 fix. See the drivetrain fix note below.' },
  { field: 'color', label: 'Color', brier: 0.2936, n: 104, status: 'overconfident' },
  { field: 'engine_cylinders', label: 'Engine cylinders', brier: 0.81, n: 5, status: 'thin_sample' },
]

export const DRIVETRAIN_CONFIDENCE_FIX = {
  before: { brier: 0.174, auc: 0.9874 },
  after: { brier: 0.164, auc: 0.9969 },
  description:
    'Of the 32 times this check ever fired, all 12 false alarms were an AWD vs 4WD listing and VIN pair. Every other pair type was correct 100% of the time. Now AWD vs 4WD mismatches report the confidence floor instead of 0.9, and every other pair still reports 0.9.',
  tradeoff:
    'Looking only at real drivetrain_swap cases, Brier got slightly worse, 0.0685 to 0.0852, since 5 real catches that happen to be AWD vs 4WD are now reported at a lower confidence despite being correct. A small trade for fixing a much bigger overconfidence problem.',
}

// Only the 5 fields that got the smooth-confidence treatment show up here.
export const SMOOTHING_CHANGES = [
  { field: 'duplicate_photos', label: 'Duplicate photo', before: 0.0625, after: 0.0025, verdict: 'improved' },
  { field: 'photo_angles', label: 'Missing angle', before: 0.0625, after: 0.0134, verdict: 'improved' },
  { field: 'mileage', label: 'Mileage', before: 0.0225, after: 0.0223, verdict: 'improved' },
  { field: 'engine_displacement', label: 'Engine displacement', before: 0.1572, after: 0.158, verdict: 'flat' },
  {
    field: 'engine_cylinders',
    label: 'Engine cylinders',
    before: 0.64,
    after: 0.81,
    verdict: 'worse',
    note: 'Only 5 real cases exist. Neither number here should be trusted much.',
  },
  {
    field: 'color',
    label: 'Color',
    before: 0.2936,
    after: 0.3835,
    verdict: 'reverted',
    note: 'Tried blending in the vision model’s own confidence, but that measures how clearly it could see the photo, not whether the color is actually wrong. It made calibration worse, so it got reverted back to the original flat number.',
  },
]

export const CONFIDENCE_FLOOR_INCIDENT = {
  floor: 0.7,
  description:
    'While building the smooth confidence formulas, an early version let scores drop below the 0.70 floor. That silently dropped 114 real catches with zero new detections gained. It was caught before shipping and fixed. The re-check after the fix found zero regressions.',
  regressionsAtShip: 0,
}
