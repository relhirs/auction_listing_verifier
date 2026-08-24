// Source: eval/results.json, analysis/output/bootstrap_ci.json,
// analysis/output/drivetrain_fix_significance.json,
// analysis/output/cost_per_catch.json. All percentages as 0-1, all costs
// in USD.
//
// Cost figures corrected 2026-08-23: every real eval call goes through
// the Anthropic Message Batches API (50% off standard rates), but
// core/logger.calculate_cost() was computing cost at standard rates with
// no batch discount applied. That overstated every cost figure here by
// exactly 2x (confirmed against the real Anthropic console total spend).
// Fixed in core/logger.py and backfilled via
// eval/apply_batch_discount_backfill.py, zero new API cost since it only
// rescales already-logged token counts.

export const HEADLINE = {
  overallAccuracy: 0.875,
  tp: 456,
  n: 500,
  // three real points in the project's history, not a smooth curve
  accuracyTrajectory: [0.775, 0.865, 0.875],
  trajectoryLabels: ['Before the fixes', 'After make_error fix', 'After drivetrain_swap fix'],
  // naiveBaseline is the majority-class guess: always predicting "needs
  // review", the single most common expected verdict (255 of 497 real
  // listings). flagEverythingBaseline is a different, real baseline:
  // always predicting "reject" for every listing (202 of 497, 0.4064).
  // These were previously conflated, the chart labeled naiveBaseline as
  // "flag everything" when it is actually the majority-class guess.
  naiveBaseline: 0.513,
  flagEverythingBaseline: 0.4064,
  improvementPoints: 36,
  totalCostUsd: 60.2112,
  avgCostPerListingUsd: 0.1211,
  costPerSuccessfulCatchUsd: 0.132,
  wastedCostUsd: 4.5727,
  wastedCostPct: 0.0759,
}

export const BOOTSTRAP_CI = {
  pointEstimate: 0.8753,
  ciLow: 0.8451,
  ciHigh: 0.9034,
  bootstrapSe: 0.0149,
  resamples: 5000,
  n: 500,
}

export const MCNEMAR = {
  before: { recall: 0.65, caught: 13, missed: 7, n: 20 },
  after: { recall: 1.0, caught: 20, missed: 0, n: 20 },
  bothCaught: 13,
  bothMissed: 0,
  fixedMissedToCaught: 7,
  brokeCaughtToMissed: 0,
  contingencyTable: [
    [13, 0],
    [7, 0],
  ],
  statistic: 0.0,
  pValue: 0.015625,
  significant: true,
  discordantPairs: 7,
  correctionNote: {
    wrongTest: "Fisher's exact test",
    wrongP: 0.0083,
    correctTest: "McNemar's exact test (paired)",
    correctP: 0.015625,
    note: 'Fisher assumes two independent groups. This is the same 20 auctions measured twice, so it needed a paired test instead. Same conclusion either way, just a different exact number. Caught during a later review.',
  },
  powerNote:
    'Only 7 of 20 pairs actually flipped. A test with more listings would carry more weight, but the real proof here is that every one of those misses was traced back to its exact cause in the code, not just inferred from a p value.',
}
