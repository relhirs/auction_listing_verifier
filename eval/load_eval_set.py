"""
load_eval_set.py
Loads the Cars & Bids eval CSV into a list of dictionaries,
with light type coercion for numeric and boolean fields.
"""

import csv
from pathlib import Path


# Fields that should be integers
INT_FIELDS = {"year", "mileage", "asking_price", "error_subtlety"}

# Fields that should be booleans (stored as "yes" / "no" in the CSV)
BOOL_FIELDS = {
    "vin_checkable",
    "requires_visual_confirmation",
    "seller_description_contains_error",
}

# Fields that are comma-separated lists
LIST_FIELDS = {"photo_angles_present", "cross_reference_fields"}


def _coerce(key: str, value: str) -> object:
    """Convert a raw CSV string to the appropriate Python type."""
    if key in INT_FIELDS:
        return int(value) if value else None
    if key in BOOL_FIELDS:
        return value.strip().lower() == "yes"
    if key in LIST_FIELDS:
        return [item.strip() for item in value.split(",") if item.strip()]
    return value  # keep everything else as a plain string


def load_eval_set(csv_path: str | Path) -> list[dict]:
    """
    Read the eval CSV and return a list of dicts, one per listing.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of listing dicts with coerced types.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    listings = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            listing = {key: _coerce(key, value) for key, value in row.items()}
            listings.append(listing)

    return listings


if __name__ == "__main__":
    # Resolve relative to this script's location so it works from any cwd
    csv_path = Path(__file__).parent / "cars_bids_eval_errors.csv"
    listings = load_eval_set(csv_path)

for listing in listings:
    print(f"\n{listing['listing_id']} — {listing['year']} {listing['make']} {listing['model']}")
    print(f"  error_type:    {listing['error_type']}")
    print(f"  error_field:   {listing['error_field']}")
    print(f"  claimed_value: {listing['claimed_value']}")
    print(f"  correct_value: {listing['correct_value']}")