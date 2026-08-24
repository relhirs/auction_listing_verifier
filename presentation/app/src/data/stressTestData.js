// Source: analysis/output/threshold_sensitivity.json (by_threshold, copied
// verbatim), analysis/output/injection_reweighting.json,
// analysis/output/photo_sampling_tradeoff.json.

export const THRESHOLD_SWEEP = [0.3, 0.4, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
export const CONFIDENCE_FLOOR = 0.7

// Keyed by threshold as a string, then by error_type: {tp, fn, fp, precision, recall, f1}
export const BY_THRESHOLD = {
  '0.3': {
    year_error: { tp: 125, fn: 25, fp: 162, precision: 0.4355, recall: 0.8333, f1: 0.5721 },
    make_error: { tp: 52, fn: 0, fp: 51, precision: 0.5049, recall: 1.0, f1: 0.671 },
    transmission_swap: { tp: 27, fn: 1, fp: 21, precision: 0.5625, recall: 0.9643, f1: 0.7105 },
    engine_error: { tp: 44, fn: 5, fp: 42, precision: 0.5116, recall: 0.898, f1: 0.6519 },
    color_error: { tp: 52, fn: 2, fp: 51, precision: 0.5049, recall: 0.963, f1: 0.6624 },
    duplicate_photo: { tp: 51, fn: 4, fp: 70, precision: 0.4215, recall: 0.9273, f1: 0.5795 },
    missing_angle: { tp: 51, fn: 4, fp: 78, precision: 0.3953, recall: 0.9273, f1: 0.5543 },
    mileage_drift: { tp: 34, fn: 0, fp: 38, precision: 0.4722, recall: 1.0, f1: 0.6415 },
    drivetrain_swap: { tp: 20, fn: 0, fp: 4, precision: 0.8333, recall: 1.0, f1: 0.9091 },
  },
  '0.4': {
    year_error: { tp: 125, fn: 25, fp: 161, precision: 0.4371, recall: 0.8333, f1: 0.5734 },
    make_error: { tp: 52, fn: 0, fp: 49, precision: 0.5149, recall: 1.0, f1: 0.6797 },
    transmission_swap: { tp: 27, fn: 1, fp: 21, precision: 0.5625, recall: 0.9643, f1: 0.7105 },
    engine_error: { tp: 44, fn: 5, fp: 42, precision: 0.5116, recall: 0.898, f1: 0.6519 },
    color_error: { tp: 52, fn: 2, fp: 51, precision: 0.5049, recall: 0.963, f1: 0.6624 },
    duplicate_photo: { tp: 51, fn: 4, fp: 70, precision: 0.4215, recall: 0.9273, f1: 0.5795 },
    missing_angle: { tp: 51, fn: 4, fp: 77, precision: 0.3984, recall: 0.9273, f1: 0.5574 },
    mileage_drift: { tp: 34, fn: 0, fp: 38, precision: 0.4722, recall: 1.0, f1: 0.6415 },
    drivetrain_swap: { tp: 20, fn: 0, fp: 4, precision: 0.8333, recall: 1.0, f1: 0.9091 },
  },
  '0.5': {
    year_error: { tp: 125, fn: 25, fp: 12, precision: 0.9124, recall: 0.8333, f1: 0.8711 },
    make_error: { tp: 52, fn: 0, fp: 15, precision: 0.7761, recall: 1.0, f1: 0.8739 },
    transmission_swap: { tp: 27, fn: 1, fp: 6, precision: 0.8182, recall: 0.9643, f1: 0.8852 },
    engine_error: { tp: 44, fn: 5, fp: 12, precision: 0.7857, recall: 0.898, f1: 0.8381 },
    color_error: { tp: 52, fn: 2, fp: 12, precision: 0.8125, recall: 0.963, f1: 0.8814 },
    duplicate_photo: { tp: 51, fn: 4, fp: 21, precision: 0.7083, recall: 0.9273, f1: 0.8031 },
    missing_angle: { tp: 51, fn: 4, fp: 25, precision: 0.6711, recall: 0.9273, f1: 0.7786 },
    mileage_drift: { tp: 34, fn: 0, fp: 12, precision: 0.7391, recall: 1.0, f1: 0.85 },
    drivetrain_swap: { tp: 20, fn: 0, fp: 2, precision: 0.9091, recall: 1.0, f1: 0.9524 },
  },
  '0.6': {
    year_error: { tp: 125, fn: 25, fp: 12, precision: 0.9124, recall: 0.8333, f1: 0.8711 },
    make_error: { tp: 52, fn: 0, fp: 15, precision: 0.7761, recall: 1.0, f1: 0.8739 },
    transmission_swap: { tp: 27, fn: 1, fp: 6, precision: 0.8182, recall: 0.9643, f1: 0.8852 },
    engine_error: { tp: 44, fn: 5, fp: 8, precision: 0.8462, recall: 0.898, f1: 0.8713 },
    color_error: { tp: 52, fn: 2, fp: 4, precision: 0.9286, recall: 0.963, f1: 0.9455 },
    duplicate_photo: { tp: 51, fn: 4, fp: 12, precision: 0.8095, recall: 0.9273, f1: 0.8644 },
    missing_angle: { tp: 51, fn: 4, fp: 13, precision: 0.7969, recall: 0.9273, f1: 0.8571 },
    mileage_drift: { tp: 34, fn: 0, fp: 8, precision: 0.8095, recall: 1.0, f1: 0.8947 },
    drivetrain_swap: { tp: 20, fn: 0, fp: 2, precision: 0.9091, recall: 1.0, f1: 0.9524 },
  },
  '0.65': {
    year_error: { tp: 125, fn: 25, fp: 12, precision: 0.9124, recall: 0.8333, f1: 0.8711 },
    make_error: { tp: 52, fn: 0, fp: 15, precision: 0.7761, recall: 1.0, f1: 0.8739 },
    transmission_swap: { tp: 27, fn: 1, fp: 6, precision: 0.8182, recall: 0.9643, f1: 0.8852 },
    engine_error: { tp: 44, fn: 5, fp: 8, precision: 0.8462, recall: 0.898, f1: 0.8713 },
    color_error: { tp: 52, fn: 2, fp: 4, precision: 0.9286, recall: 0.963, f1: 0.9455 },
    duplicate_photo: { tp: 51, fn: 4, fp: 12, precision: 0.8095, recall: 0.9273, f1: 0.8644 },
    missing_angle: { tp: 51, fn: 4, fp: 13, precision: 0.7969, recall: 0.9273, f1: 0.8571 },
    mileage_drift: { tp: 34, fn: 0, fp: 8, precision: 0.8095, recall: 1.0, f1: 0.8947 },
    drivetrain_swap: { tp: 20, fn: 0, fp: 2, precision: 0.9091, recall: 1.0, f1: 0.9524 },
  },
  '0.7': {
    year_error: { tp: 125, fn: 25, fp: 12, precision: 0.9124, recall: 0.8333, f1: 0.8711 },
    make_error: { tp: 52, fn: 0, fp: 15, precision: 0.7761, recall: 1.0, f1: 0.8739 },
    transmission_swap: { tp: 27, fn: 1, fp: 6, precision: 0.8182, recall: 0.9643, f1: 0.8852 },
    engine_error: { tp: 44, fn: 5, fp: 8, precision: 0.8462, recall: 0.898, f1: 0.8713 },
    color_error: { tp: 52, fn: 2, fp: 4, precision: 0.9286, recall: 0.963, f1: 0.9455 },
    duplicate_photo: { tp: 51, fn: 4, fp: 12, precision: 0.8095, recall: 0.9273, f1: 0.8644 },
    missing_angle: { tp: 51, fn: 4, fp: 13, precision: 0.7969, recall: 0.9273, f1: 0.8571 },
    mileage_drift: { tp: 34, fn: 0, fp: 8, precision: 0.8095, recall: 1.0, f1: 0.8947 },
    drivetrain_swap: { tp: 20, fn: 0, fp: 2, precision: 0.9091, recall: 1.0, f1: 0.9524 },
  },
  '0.75': {
    year_error: { tp: 125, fn: 25, fp: 12, precision: 0.9124, recall: 0.8333, f1: 0.8711 },
    make_error: { tp: 52, fn: 0, fp: 14, precision: 0.7879, recall: 1.0, f1: 0.8814 },
    transmission_swap: { tp: 27, fn: 1, fp: 6, precision: 0.8182, recall: 0.9643, f1: 0.8852 },
    engine_error: { tp: 44, fn: 5, fp: 8, precision: 0.8462, recall: 0.898, f1: 0.8713 },
    color_error: { tp: 52, fn: 2, fp: 4, precision: 0.9286, recall: 0.963, f1: 0.9455 },
    duplicate_photo: { tp: 51, fn: 4, fp: 12, precision: 0.8095, recall: 0.9273, f1: 0.8644 },
    missing_angle: { tp: 51, fn: 4, fp: 13, precision: 0.7969, recall: 0.9273, f1: 0.8571 },
    mileage_drift: { tp: 34, fn: 0, fp: 8, precision: 0.8095, recall: 1.0, f1: 0.8947 },
    drivetrain_swap: { tp: 15, fn: 5, fp: 2, precision: 0.8824, recall: 0.75, f1: 0.8108 },
  },
  '0.8': {
    year_error: { tp: 125, fn: 25, fp: 5, precision: 0.9615, recall: 0.8333, f1: 0.8929 },
    make_error: { tp: 52, fn: 0, fp: 7, precision: 0.8814, recall: 1.0, f1: 0.9369 },
    transmission_swap: { tp: 27, fn: 1, fp: 3, precision: 0.9, recall: 0.9643, f1: 0.931 },
    engine_error: { tp: 44, fn: 5, fp: 2, precision: 0.9565, recall: 0.898, f1: 0.9263 },
    color_error: { tp: 0, fn: 54, fp: 4, precision: 0.0, recall: 0.0, f1: null },
    duplicate_photo: { tp: 51, fn: 4, fp: 6, precision: 0.8947, recall: 0.9273, f1: 0.9107 },
    missing_angle: { tp: 51, fn: 4, fp: 3, precision: 0.9444, recall: 0.9273, f1: 0.9358 },
    mileage_drift: { tp: 23, fn: 11, fp: 2, precision: 0.92, recall: 0.6765, f1: 0.7797 },
    drivetrain_swap: { tp: 15, fn: 5, fp: 0, precision: 1.0, recall: 0.75, f1: 0.8571 },
  },
  '0.85': {
    year_error: { tp: 125, fn: 25, fp: 4, precision: 0.969, recall: 0.8333, f1: 0.8961 },
    make_error: { tp: 52, fn: 0, fp: 6, precision: 0.8966, recall: 1.0, f1: 0.9455 },
    transmission_swap: { tp: 0, fn: 28, fp: 3, precision: 0.0, recall: 0.0, f1: null },
    engine_error: { tp: 44, fn: 5, fp: 2, precision: 0.9565, recall: 0.898, f1: 0.9263 },
    color_error: { tp: 0, fn: 54, fp: 3, precision: 0.0, recall: 0.0, f1: null },
    duplicate_photo: { tp: 51, fn: 4, fp: 4, precision: 0.9273, recall: 0.9273, f1: 0.9273 },
    missing_angle: { tp: 48, fn: 7, fp: 2, precision: 0.96, recall: 0.8727, f1: 0.9143 },
    mileage_drift: { tp: 23, fn: 11, fp: 2, precision: 0.92, recall: 0.6765, f1: 0.7797 },
    drivetrain_swap: { tp: 15, fn: 5, fp: 0, precision: 1.0, recall: 0.75, f1: 0.8571 },
  },
  '0.9': {
    year_error: { tp: 125, fn: 25, fp: 4, precision: 0.969, recall: 0.8333, f1: 0.8961 },
    make_error: { tp: 52, fn: 0, fp: 6, precision: 0.8966, recall: 1.0, f1: 0.9455 },
    transmission_swap: { tp: 0, fn: 28, fp: 3, precision: 0.0, recall: 0.0, f1: null },
    engine_error: { tp: 44, fn: 5, fp: 2, precision: 0.9565, recall: 0.898, f1: 0.9263 },
    color_error: { tp: 0, fn: 54, fp: 3, precision: 0.0, recall: 0.0, f1: null },
    duplicate_photo: { tp: 51, fn: 4, fp: 4, precision: 0.9273, recall: 0.9273, f1: 0.9273 },
    missing_angle: { tp: 12, fn: 43, fp: 2, precision: 0.8571, recall: 0.2182, f1: 0.3478 },
    mileage_drift: { tp: 23, fn: 11, fp: 2, precision: 0.92, recall: 0.6765, f1: 0.7797 },
    drivetrain_swap: { tp: 15, fn: 5, fp: 0, precision: 1.0, recall: 0.75, f1: 0.8571 },
  },
  '0.95': {
    year_error: { tp: 125, fn: 25, fp: 3, precision: 0.9766, recall: 0.8333, f1: 0.8993 },
    make_error: { tp: 52, fn: 0, fp: 1, precision: 0.9811, recall: 1.0, f1: 0.9905 },
    transmission_swap: { tp: 0, fn: 28, fp: 1, precision: 0.0, recall: 0.0, f1: null },
    engine_error: { tp: 44, fn: 5, fp: 0, precision: 1.0, recall: 0.898, f1: 0.9462 },
    color_error: { tp: 0, fn: 54, fp: 1, precision: 0.0, recall: 0.0, f1: null },
    duplicate_photo: { tp: 51, fn: 4, fp: 0, precision: 1.0, recall: 0.9273, f1: 0.9623 },
    missing_angle: { tp: 0, fn: 55, fp: 2, precision: 0.0, recall: 0.0, f1: null },
    mileage_drift: { tp: 21, fn: 13, fp: 1, precision: 0.9545, recall: 0.6176, f1: 0.75 },
    drivetrain_swap: { tp: 0, fn: 20, fp: 0, precision: null, recall: 0.0, f1: null },
  },
}

export const THRESHOLD_NOTES = {
  drivetrain_swap: {
    metric: 'Recall',
    text:
      'Green bar drops from 100% to 75% once the floor is raised to 0.75 or above. That drop is real, not noise: 5 of the 20 real catches are AWD vs 4WD mismatches, which this check deliberately reports at a lower confidence because that specific pair is a much weaker signal than any other drivetrain mismatch. Raise the floor past where that lower confidence sits, and those 5 catches get thrown out. At the real 0.70 floor, none of this happens, recall is still a full 100%.',
  },
  missing_angle: {
    metric: 'Precision',
    text:
      'Blue bar falls from 79.7% at the real 0.70 floor down to about 39.5% at 0.30. Lowering the floor lets in far more noisy, low-confidence flags without catching any more real errors, so a shrinking share of everything it flags is actually correct.',
  },
}

// analysis/output/injection_reweighting.json
export const INJECTION_REWEIGHTING = {
  current_realized: { label: 'As tested', meanRecall: 0.9173, meanVerdictAccuracy: 0.8753 },
  uniform: { label: 'Equal weight', meanRecall: 0.9458, meanVerdictAccuracy: 0.9045 },
  real_world_informed: { label: 'Real world mix', meanRecall: 0.9434, meanVerdictAccuracy: 0.9693 },
}

export const REAL_WORLD_ERROR_COUNTS = [
  { category: 'VIN or spec mismatch', count: 19 },
  { category: 'Duplicate photo', count: 3 },
  { category: 'Undisclosed damage', count: 1 },
  { category: 'Odometer discrepancy', count: 1 },
]

// Real sample size (tp + fn at the 0.70 floor, from BY_THRESHOLD above) per
// injected error type -- how uneven this eval set actually is, which is
// exactly what "equal weight" flattens out.
export const ERROR_TYPE_SAMPLE_SIZES = [
  { label: 'Year', n: 150 },
  { label: 'Duplicate photo', n: 55 },
  { label: 'Missing angle', n: 55 },
  { label: 'Color', n: 54 },
  { label: 'Make', n: 52 },
  { label: 'Engine', n: 49 },
  { label: 'Mileage', n: 34 },
  { label: 'Transmission', n: 28 },
  { label: 'Drivetrain', n: 20 },
]

// Condensed, one-line, plain-English version of each real case's `summary`
// field from corpus/seed_verified_community_errors.py (which seeds
// corpus.db's verified_community_errors table) -- what a real person
// actually found wrong, not just the bucket label. `category` matches
// REAL_WORLD_ERROR_COUNTS's category strings. A few cases' bucket is an
// approximate best fit against this project's fixed 4-category taxonomy --
// see the caveat rendered alongside this data, not silently smoothed over.
export const COMMUNITY_ERROR_CASES = [
  {
    category: 'VIN or spec mismatch',
    summary:
      "Turbo-spec engine details didn't match an '85.5 model; seller confirmed only the transaxle was swapped, not the engine.",
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      'Intake manifold casting number identifies a part that was never used on the specific engine the listing associates with this car.',
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      "Transmission listed with a generic label because the site has no DSG option, even though every '15 TDI actually uses DSG.",
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      "Listing implied the car has power brakes; seller confirmed it doesn't, likely changed by a previous owner.",
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      'Highlights section had duplicate bullet points, an editorial slip caught by a commenter, not a factual spec error.',
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      "Engine marketed as a specific swap, but that exact engine was never produced in the configuration actually installed.",
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      'Aftermarket carburetors and trim emblems misrepresented as factory; the site confirmed and corrected the listing after the seller shared new photos.',
  },
  {
    category: 'VIN or spec mismatch',
    summary: 'Listing claimed cloth-and-vinyl upholstery, but the interior has no cloth at all.',
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      'Car left the factory as a base model with a package added, not the true factory trim the listing named it after.',
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      'Headline advertised a specific aftermarket coilover brand; photos actually show a different suspension kit entirely.',
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      'Listing claimed a power-operated soft top; only a higher trim actually got that feature, and this is the base model.',
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      'Listed horsepower and torque figures were for a higher trim; this car is the lower-output base model.',
  },
  {
    category: 'VIN or spec mismatch',
    summary: 'Car was concurrently listed for sale on another website while this auction was live.',
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      'Listing text implied no reserve; site staff confirmed it was a typo and corrected it to a Reserve auction.',
  },
  {
    category: 'VIN or spec mismatch',
    summary: 'Fitted wheels identified as a different brand than the one stated in the listing.',
  },
  {
    category: 'VIN or spec mismatch',
    summary: 'Tires visible in the photos are a different brand than the one stated in the listing text.',
  },
  {
    category: 'VIN or spec mismatch',
    summary:
      'Instrument cluster and engine identified as swapped-in parts from other cars, not disclosed anywhere in the listing.',
  },
  {
    category: 'VIN or spec mismatch',
    summary: "Apparent frame rot near the torque boxes, visible in the listing's own photos, went undisclosed.",
  },
  {
    category: 'VIN or spec mismatch',
    summary: 'Trim tag decodes the factory paint color differently than what the listing states.',
  },
  {
    category: 'Duplicate photo',
    summary:
      "Known Flaws section described a more serious steering issue than the shop's actual inspection found (approximate category match -- this case is really about a disclosure gap, not a duplicate image).",
  },
  {
    category: 'Duplicate photo',
    summary: 'Same VIN found listed for sale concurrently on 3 separate marketplace listings by different sellers.',
  },
  {
    category: 'Duplicate photo',
    summary: 'Same VIN found listed concurrently on two other sites while this auction was live.',
  },
  {
    category: 'Undisclosed damage',
    summary: 'An earlier listing for the same VIN showed a larger dent than what this listing disclosed.',
  },
  {
    category: 'Odometer discrepancy',
    summary:
      'Independently traceable ownership history existed for this VIN that the listing never disclosed or addressed (approximate category match -- this case is really about ownership history, not the odometer itself).',
  },
]

export const REWEIGHTING_NOTE =
  'The mix this system was actually tested on is the lowest scoring of the three. 87.5% is not being flattered by an easy error mix. If anything, real world performance is probably a little better than that number.'

// analysis/output/photo_sampling_tradeoff.json
export const K_VALUES = [2, 3, 4, 5, 6, 7, 8, 'full']

export const RECALL_CURVES = {
  missing_angle: [
    { k: 2, meanRecall: 0.9974, ciLow: 0.9929, ciHigh: 1.0 },
    { k: 3, meanRecall: 0.9955, ciLow: 0.9891, ciHigh: 1.0 },
    { k: 4, meanRecall: 0.9937, ciLow: 0.9854, ciHigh: 1.0 },
    { k: 5, meanRecall: 0.9925, ciLow: 0.984, ciHigh: 1.0 },
    { k: 6, meanRecall: 0.9895, ciLow: 0.9785, ciHigh: 1.0 },
    { k: 7, meanRecall: 0.9853, ciLow: 0.9704, ciHigh: 1.0 },
    { k: 8, meanRecall: 0.9822, ciLow: 0.9645, ciHigh: 0.9999 },
    { k: 'full', meanRecall: 0.9273, ciLow: 0.858, ciHigh: 0.9965 },
  ],
  duplicate_photo: [
    { k: 2, meanRecall: 0.0205, ciLow: 0.016, ciHigh: 0.0249 },
    { k: 3, meanRecall: 0.0536, ciLow: 0.0427, ciHigh: 0.0646 },
    { k: 4, meanRecall: 0.1056, ciLow: 0.0851, ciHigh: 0.1262 },
    { k: 5, meanRecall: 0.165, ciLow: 0.1398, ciHigh: 0.1902 },
    { k: 6, meanRecall: 0.2274, ciLow: 0.191, ciHigh: 0.2637 },
    { k: 7, meanRecall: 0.297, ciLow: 0.2522, ciHigh: 0.3418 },
    { k: 8, meanRecall: 0.3675, ciLow: 0.3177, ciHigh: 0.4172 },
    { k: 'full', meanRecall: 0.9273, ciLow: 0.858, ciHigh: 0.9965 },
  ],
  color_error: [
    { k: 2, meanRecall: 0.8498, ciLow: 0.8053, ciHigh: 0.8943 },
    { k: 3, meanRecall: 0.9205, ciLow: 0.8775, ciHigh: 0.9634 },
    { k: 4, meanRecall: 0.9474, ciLow: 0.9061, ciHigh: 0.9887 },
    { k: 5, meanRecall: 0.9592, ciLow: 0.9191, ciHigh: 0.9992 },
    { k: 6, meanRecall: 0.9645, ciLow: 0.9236, ciHigh: 1.0 },
    { k: 7, meanRecall: 0.9685, ciLow: 0.9285, ciHigh: 1.0 },
    { k: 8, meanRecall: 0.9695, ciLow: 0.9287, ciHigh: 1.0 },
    { k: 'full', meanRecall: 0.963, ciLow: 0.9121, ciHigh: 1.0 },
  ],
}

export const DUPLICATE_PHOTO_NOTE =
  'Catching a duplicate photo needs both copies of the same image to survive being in the sample. At k=2 that almost never happens by chance, so recall starts near zero and climbs slowly. Checked against the exact math for that (a hypergeometric probability), and it lines up.'

// Cost figures corrected 2026-08-23 for the Anthropic Batch API's 50%
// discount, previously overstated 2x (see metricsData.js's note).
export const COST_CURVE = [
  { k: 1, avgCostPerListingUsd: 0.026971 },
  { k: 2, avgCostPerListingUsd: 0.031748 },
  { k: 3, avgCostPerListingUsd: 0.036526 },
  { k: 4, avgCostPerListingUsd: 0.041303 },
  { k: 5, avgCostPerListingUsd: 0.04608 },
  { k: 6, avgCostPerListingUsd: 0.050858 },
  { k: 7, avgCostPerListingUsd: 0.055635 },
  { k: 8, avgCostPerListingUsd: 0.060412 },
  { k: 9, avgCostPerListingUsd: 0.065189 },
  { k: 10, avgCostPerListingUsd: 0.069967 },
  { k: 11, avgCostPerListingUsd: 0.074744 },
]

export const CURRENT_OPERATING_POINT = {
  avgPhotosPerListing: 20.43,
  avgCostPerListingUsd: 0.119776,
  recallAtFullSampling: { missing_angle: 0.927, duplicate_photo: 0.927, color_error: 0.963 },
}
