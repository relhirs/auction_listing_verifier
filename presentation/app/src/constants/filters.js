export const WEIGHTING_SCHEMES = [
  { id: 'current_realized', label: 'As tested' },
  { id: 'uniform', label: 'Equal weight' },
  { id: 'real_world_informed', label: 'Real world mix' },
]

export const ERROR_TYPES = [
  'year_error',
  'make_error',
  'transmission_swap',
  'engine_error',
  'color_error',
  'duplicate_photo',
  'missing_angle',
  'mileage_drift',
  'drivetrain_swap',
]

export const ERROR_TYPE_LABELS = {
  year_error: 'Year',
  make_error: 'Make',
  transmission_swap: 'Transmission',
  engine_error: 'Engine',
  color_error: 'Color',
  duplicate_photo: 'Duplicate photo',
  missing_angle: 'Missing angle',
  mileage_drift: 'Mileage drift',
  drivetrain_swap: 'Drivetrain',
}

// Status badges used in the economics table and calibration views
export const STATUS_BADGE = {
  RELIABLE: 'reliable',
  THIN_SAMPLE: 'thin_sample',
  REVERTED: 'reverted',
  ARTIFACT: 'artifact',
  OVERCONFIDENT: 'overconfident',
  WELL_CALIBRATED: 'well_calibrated',
}
