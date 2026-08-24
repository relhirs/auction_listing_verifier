REQUIRED_PHOTO_ANGLES = [
    "front", "front three-quarter", "rear", "rear three-quarter",
    "driver side profile", "passenger side profile",
    "wheels and tires",
    "interior dashboard", "interior front seats", "interior rear seats",
    "trunk or cargo area",
    "engine bay", "undercarriage",
    "odometer", "vin plate",
    "title or documents",
]

# NHTSA manufacturer name -> common brand names it decodes to.
MANUFACTURER_ALIASES: dict[str, list[str]] = {
    "am general":         ["hummer"],
    "fca us llc":         ["dodge", "chrysler", "jeep", "ram"],
    "ford motor company": ["ford"],
    "general motors":     ["chevrolet", "gmc", "cadillac", "buick"],
    "stellantis":         ["dodge", "chrysler", "jeep", "ram"],
}

# --- Thresholds (all unvalidated judgment calls) ---
CONFIDENCE_FLOOR = 0.70
ENGINE_DISPLACEMENT_TOLERANCE = 0.2
MILEAGE_TOLERANCE_MILES = 5000  # how far a Carfax-style service checkpoint
COLOR_MISMATCH_MAJORITY = 0.5
DUPLICATE_PHOTO_HASH_DISTANCE = 5  # out of 64-bit phash; lower = stricter
