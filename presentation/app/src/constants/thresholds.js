// Real tolerance constants from core/constants.py. Stated in the project
// docs as judgment calls, not empirically derived (mileage tolerance is
// the one that got a real validation pass).

export const CONFIDENCE_FLOOR = 0.7
export const ENGINE_DISPLACEMENT_TOLERANCE = 0.2
export const MILEAGE_TOLERANCE_MILES = 5000
export const COLOR_MISMATCH_MAJORITY = 0.5
export const DUPLICATE_PHOTO_HASH_DISTANCE = 5

// The 11 real sweep points analysis/threshold_sensitivity.py tested.
// The slider snaps to these, it never interpolates between them.
export const THRESHOLD_SWEEP = [0.3, 0.4, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
