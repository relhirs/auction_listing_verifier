export const INSIGHTS = [
  {
    id: 'input_isolation',
    title: 'Smart models will quietly fix your dirty test data if you do not force them to stay blind',
    lines: [
      'The extraction model noticed a planted fake detail did not match the rest of the car writeup and quietly corrected it back to the truth before the checking step ever ran.',
      'What looked like a detection failure was actually a bug in the test setup itself.',
      'Rewriting the surrounding text so the lie could not be corrected away fixed it. Make recall went from 12.50% to 100.00%.',
    ],
  },
  {
    id: 'statistical_verification',
    title: 'Fixing a bug completely can erase the statistical proof that it ever mattered',
    lines: [
      'A logistic regression was built to prove the prose patch fix had a real effect on getting caught.',
      'While the bug still lived in the drivetrain and make checks, the test showed a strong significant benefit with an odds ratio of 2.57.',
      'Once those root causes were fully fixed and misses dropped to zero, the sample got too small for the statistical model to detect the effect anymore.',
    ],
  },
  {
    id: 'methodological_rigor',
    title: 'Never trust a statistical test just because it runs without throwing an error',
    lines: [
      "The drivetrain fix was first checked with Fisher's exact test, which gave a clean p value of 0.0083.",
      "That was the wrong test. Fisher's assumes two independent groups, but this was the same 20 auctions measured twice.",
      "Switching to the correct paired test, McNemar's exact test, gave p = 0.0156. Same conclusion, but now the math actually matches what was measured.",
    ],
  },
  {
    id: 'calibration_integrity',
    title: 'Real engineering maturity means throwing away an intuitive fix when the data says no',
    lines: [
      'Drivetrain and color checks sounded just as confident on false alarms as they did on real catches.',
      "Blending in the vision model's own confidence score seemed like the obvious fix, but it made the Brier calibration score worse, going from 0.29 to 0.38.",
      'The idea got reverted and written down as a dead end instead of kept around just because it sounded clean.',
    ],
  },
]

export const LIMITATIONS = [
  {
    text: 'Engine cylinders has exactly 1 real case in the whole 500 listing set. Its AUC is close to a coin flip because there just is not enough data, not because the check is bad.',
    badge: 'n=1',
  },
  {
    text: 'Listings from before 1981 have VINs that are too short for NHTSA to decode a model year at all. Those cannot be graded on year, structurally.',
    badge: 'structural gap',
  },
  {
    text: 'The numeric tolerances (confidence floor 0.70, mileage tolerance 5000 miles, engine displacement tolerance 0.2, color majority 0.5, photo hash distance 5) are judgment calls, not numbers pulled from a study.',
    badge: 'unvalidated',
  },
]

export const FUTURE_WORK = [
  {
    category: 'Data pipeline',
    items: [
      {
        title: 'Give each row its own random seed',
        text: 'The whole eval set once pulled from a single shared random stream. Changing one error injector shifted 259 of 497 rows that had nothing to do with that injector. I found that bug and fixed it for that one case by giving the ground truth regen its own seed. I never went back and reseeded every row in the whole pipeline by its own auction ID. That would mean touching a pipeline that already produces validated results, to guard against a bug class I already caught and patched. Worth doing before adding more randomized steps. Not urgent enough to justify the risk right now.',
      },
    ],
  },
  {
    category: 'Evaluation methodology',
    items: [
      {
        title: 'Split off a real holdout set',
        text: 'Every numeric tolerance in this project, like the 5,000 mile drift cutoff, was set by judgment and then tested against the same 500 listings used for the headline accuracy number. Splitting those into a tuning set and a separate reported set would let the accuracy number stand on its own instead of being measured against the same data it was tuned on.',
      },
      {
        title: 'Build the near threshold hard case injector',
        text: 'This would plant fake errors right at the edge of a numeric cutoff, like a car exactly 5,000 miles off instead of wildly off, and see where the check actually starts missing them. Right now there is no real way to tell if 5,000 miles is a good number or just a reasonable guess. I did not build it because doing it right needs real cases clustered near that edge in real numbers, and 500 listings does not give you enough density near any single cutoff to trust the result. It would take a meaningfully bigger dataset before this test told you anything you could actually believe.',
      },
      {
        title: 'Benchmark a second model for photo checks',
        text: 'GPT 4o was on the table as an alternative for photo analysis. I never tested it against Claude. There was no signal that the current photo agent was underperforming, and running a second full vision pass across every listing photo just to compare costs real money for a question I did not have evidence needed answering. If the eval ever shows photo checks are the weak link, this is the first place I would look.',
      },
    ],
  },
  {
    category: 'Verifier and calibration',
    items: [
      {
        title: 'Use real calibration methods, not hand tuned floors',
        text: 'Right now the confidence scores are scaled with floor and ceiling values I picked by hand. Something like Platt scaling or isotonic regression would fit an actual curve from data instead. I did not do this because those methods need a real number of positive cases to fit a curve that means anything, and several checks here do not have that. Engine cylinders has exactly 1 real case in the whole set. Fitting a calibration curve on that few points is not more rigorous, it is overfitting noise and calling it math. This needs a much bigger dataset before it is worth doing, and it would make a stronger data science story than the hand tuned floors do now, once there is enough data to back it.',
      },
      {
        title: 'Add structured tracing per pipeline call',
        text: 'Debugging cross agent issues, like tracking down the self correction bug, meant reading logs and rerunning things by hand. A trace log per run, one row per agent call with input, output, and timing, would make that faster next time. I skipped it because this project was a single 500 listing analysis pass, not a system running repeatedly in production. Tracing infrastructure pays for itself when you are debugging the same pipeline over and over across many runs. For a one off pass, reading logs by hand was still faster than building the tooling to avoid it.',
      },
    ],
  },
]
