// Source: analysis/output/logistic_regression_diagnostic.json.
// This tests whether the "prose patch" fix actually predicts getting
// caught, after controlling for error type. It is a diagnostic, not a
// classifier meant to run on new listings.

export const LOGISTIC_REGRESSION = {
  nUsed: 353,
  nEventsMisses: 33,
  nEventsMissesPreFix: 40,
  nPredictors: 7,
  eventsPerPredictor: 4.7,
  eppWarning:
    'The rule of thumb for a stable fit is about 10 events per predictor. This one has 4.7, close to that line. Treat the coefficients as a rough read, not a textbook clean result.',
  pseudoR2: 0.1346,
  logLikelihood: -94.8614,
  converged: false,
  referenceLevel: 'year_error',
  coefficients: [
    { name: 'Intercept', or: 6.0294, ciLow: 2.2152, ciHigh: 16.4115, p: 0.0004 },
    {
      name: 'prose_patch_applied',
      or: 1.6157,
      ciLow: 0.699,
      ciHigh: 3.7344,
      p: 0.2617,
      preFix: { or: 2.57, ciLow: 1.19, ciHigh: 5.54, p: 0.016 },
      note: 'This dropped out once the drivetrain fix landed. The fix removed the exact misses that were driving that earlier number. The earlier result was really about drivetrain, not about the prose patch itself.',
    },
    {
      name: 'color_error',
      or: 2.7584,
      ciLow: 0.5218,
      ciHigh: 14.5828,
      p: 0.2324,
    },
    {
      name: 'drivetrain_swap',
      or: 62298225.9273,
      ciLow: 0.0,
      ciHigh: Infinity,
      p: 0.9972,
      degenerate: true,
      note: 'After the fix, every drivetrain_swap row is caught. With zero variance to explain, the model has no real slope to estimate here, so the number blows up. This is a statistical artifact, not a real effect.',
    },
    {
      name: 'engine_error',
      or: 1.0341,
      ciLow: 0.294,
      ciHigh: 3.6372,
      p: 0.9584,
    },
    {
      name: 'make_error',
      or: 77.2976,
      ciLow: 0.0418,
      ciHigh: 142956.115,
      p: 0.2573,
      degenerate: true,
      note: 'Same issue as drivetrain_swap, near perfect separation after the fix makes this coefficient unstable.',
    },
    {
      name: 'transmission_swap',
      or: 2.8313,
      ciLow: 0.3184,
      ciHigh: 25.1743,
      p: 0.3505,
    },
    {
      name: 'reassigned',
      or: 0.459,
      ciLow: 0.1705,
      ciHigh: 1.2356,
      p: 0.1232,
    },
  ],
}
