from pydantic import BaseModel
from typing import Optional, Literal
import re
from agents.extraction_agent import ListingData
from agents.vin_agent import VINData
from agents.photo_agent import PhotoAnalysis
from agents.editorial_agent import EditorialFlags


# --- Flag Model ---
class VerificationSummary(BaseModel):
    year_verified: Optional[bool] = None
    year_claimed: Optional[str] = None
    year_verified_value: Optional[str] = None
    year_source: Optional[str] = None

    make_verified: Optional[bool] = None
    make_claimed: Optional[str] = None
    make_verified_value: Optional[str] = None

    engine_verified: Optional[bool] = None
    engine_claimed: Optional[str] = None
    engine_verified_value: Optional[str] = None

    color_verified: Optional[bool] = None
    color_claimed: Optional[str] = None
    color_observed: Optional[str] = None

    mileage_claimed: Optional[str] = None
    mileage_photo_read: Optional[str] = None
    mileage_consistent: Optional[bool] = None

    photos_analyzed: int = 0
    photos_with_damage: int = 0
    damage_observations: list[str] = []

    vin_decoded: bool = False
    vin_source: str = "NHTSA"

    editorial_score: Optional[float] = None
    editorial_score_label: Optional[str] = None


class Flag(BaseModel):
    field_name: str
    claimed_value: Optional[str]
    verified_value: Optional[str]
    source_of_truth: str
    confidence: float  # 0.0 to 1.0
    severity: Literal["ERROR", "WARNING", "INFO"]
    suggested_fix: str


# --- Normalization helpers ---
def normalize_color(color: Optional[str]) -> Optional[str]:
    if not color:
        return None
    color = color.lower().strip()
    # Strip manufacturer-specific color names down to base color
    base_colors = ["black", "white", "silver", "gray", "grey", "red", "blue",
                   "green", "yellow", "orange", "brown", "purple", "gold", "beige"]
    for base in base_colors:
        if base in color:
            return base
    return color


def normalize_transmission(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.lower().strip()
    if "manual" in value or "standard" in value:
        return "manual"
    if "automatic" in value or "automated" in value:
        return "automatic"
    if "cvt" in value:
        return "cvt"
    return value


def normalize_displacement(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        # Strip non-numeric characters except decimal point
        cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
        return round(float(cleaned), 1)
    except (ValueError, AttributeError):
        return None


# --- Individual comparison functions ---
def check_year(listing: ListingData, vin: VINData) -> Optional[Flag]:
    if vin.year is None:
        return Flag(
            field_name="year",
            claimed_value=str(listing.year),
            verified_value=None,
            source_of_truth="NHTSA",
            confidence=0.5,
            severity="INFO",
            suggested_fix="NHTSA did not return a model year. Verify manually."
        )
    if listing.year != vin.year:
        return Flag(
            field_name="year",
            claimed_value=str(listing.year),
            verified_value=str(vin.year),
            source_of_truth="NHTSA",
            confidence=0.95,
            severity="ERROR",
            suggested_fix=f"Listing says {listing.year} but VIN decodes to {vin.year}. Correct the listing year."
        )
    return None


def check_engine(listing: ListingData, vin: VINData) -> Optional[Flag]:
    if vin.engine_displacement is None:
        return Flag(
            field_name="engine_displacement",
            claimed_value=listing.engine,
            verified_value=None,
            source_of_truth="NHTSA",
            confidence=0.4,
            severity="INFO",
            suggested_fix="NHTSA did not return engine displacement. Verify manually."
        )

    listing_displacement = normalize_displacement(listing.engine)
    vin_displacement = normalize_displacement(vin.engine_displacement)

    if listing_displacement is None or vin_displacement is None:
        return None

    if abs(listing_displacement - vin_displacement) > 0.2:
        return Flag(
            field_name="engine_displacement",
            claimed_value=listing.engine,
            verified_value=f"{vin.engine_displacement}L ({vin.engine_cylinders} cylinders)",
            source_of_truth="NHTSA",
            confidence=0.85,
            severity="WARNING",
            suggested_fix=f"Listing engine ({listing.engine}) doesn't match NHTSA displacement ({vin.engine_displacement}L). Verify engine spec."
        )
    return None


def check_color(listing: ListingData, photos: list[PhotoAnalysis]) -> Optional[Flag]:
    # Collect all non-null color observations from photos
    photo_colors = [
        normalize_color(p.visible_color)
        for p in photos
        if p.visible_color is not None and normalize_color(p.visible_color) is not None
    ]

    if not photo_colors:
        return Flag(
            field_name="color",
            claimed_value=listing.color,
            verified_value=None,
            source_of_truth="photo_agent",
            confidence=0.3,
            severity="INFO",
            suggested_fix="No exterior color could be determined from photos. Ensure exterior photos are included."
        )

    listing_color_normalized = normalize_color(listing.color)
    mismatches = [c for c in photo_colors if c != listing_color_normalized]

    if len(mismatches) >= len(photo_colors) / 2:
        most_common = max(set(photo_colors), key=photo_colors.count)
        return Flag(
            field_name="color",
            claimed_value=listing.color,
            verified_value=most_common,
            source_of_truth="photo_agent",
            confidence=0.65,
            severity="WARNING",
            suggested_fix=f"Listed color ({listing.color}) may not match photos. Photo agent observed '{most_common}'. Verify exterior color."
        )
    return None


def check_photo_angles(photos: list[PhotoAnalysis]) -> list[Flag]:
    flags = []
    required_angles = ["front", "rear", "driver side", "passenger side",
                       "interior", "engine bay", "odometer", "undercarriage"]

    covered_angles = set()
    for photo in photos:
        # Infer present angles: any required angle not listed as missing in this photo
        photo_missing = {a.lower() for a in photo.missing_angles}
        for angle in required_angles:
            if angle not in photo_missing:
                covered_angles.add(angle)
        # Also scan notes for explicit angle mentions
        if photo.notes:
            notes_lower = photo.notes.lower()
            for angle in required_angles:
                if angle in notes_lower:
                    covered_angles.add(angle)

    confirmed_missing = [a for a in required_angles if a not in covered_angles]

    for angle in confirmed_missing:
        severity = "WARNING" if angle in ["engine bay", "undercarriage"] else "INFO"
        flags.append(Flag(
            field_name="photo_angles",
            claimed_value=None,
            verified_value=None,
            source_of_truth="photo_agent",
            confidence=0.75,
            severity=severity,
            suggested_fix=f"Standard photo angle missing: '{angle}'. Request this photo from the seller."
        ))

    return flags


# --- Manufacturer alias map (NHTSA name -> common brand names) ---
_MANUFACTURER_ALIASES: dict[str, list[str]] = {
    "am general":         ["hummer"],
    "fca us llc":         ["dodge", "chrysler", "jeep", "ram"],
    "ford motor company": ["ford"],
    "general motors":     ["chevrolet", "gmc", "cadillac", "buick"],
    "stellantis":         ["dodge", "chrysler", "jeep", "ram"],
}


def _make_aliases(make: str) -> set[str]:
    normalized = make.lower().strip()
    return set(_MANUFACTURER_ALIASES.get(normalized, [normalized]))


def check_make(listing: ListingData, vin: VINData) -> Optional[Flag]:
    if vin.make is None:
        return None
    if not _make_aliases(listing.make).isdisjoint(_make_aliases(vin.make)):
        return None
    return Flag(
        field_name="make",
        claimed_value=listing.make,
        verified_value=vin.make,
        source_of_truth="NHTSA",
        confidence=0.99,
        severity="ERROR",
        suggested_fix=f"Listing make ({listing.make}) does not match VIN ({vin.make}). This is a critical error."
    )


def check_mileage_vs_odometer(listing: ListingData, photos: list[PhotoAnalysis]) -> Optional[Flag]:
    # Look for odometer readings in photo notes
    for photo in photos:
        if photo.notes and "odometer" in photo.notes.lower():
            # Extract any number from the notes that looks like mileage
            numbers = re.findall(r'\b\d{4,6}\b', photo.notes)
            for num in numbers:
                odometer_reading = int(num)
                if listing.mileage and abs(odometer_reading - listing.mileage) > 500:
                    return Flag(
                        field_name="mileage",
                        claimed_value=str(listing.mileage),
                        verified_value=str(odometer_reading),
                        source_of_truth="photo_agent",
                        confidence=0.75,
                        severity="WARNING",
                        suggested_fix=f"Listed mileage ({listing.mileage}) differs from odometer photo ({odometer_reading}). Verify current mileage."
                    )
    return None


def build_verification_summary(
    listing_data: ListingData,
    vin_data: VINData,
    photo_data: list[PhotoAnalysis],
    editorial_data: EditorialFlags,
) -> VerificationSummary:
    s = VerificationSummary()

    # Year
    s.year_claimed = str(listing_data.year) if listing_data.year else None
    if vin_data.year is not None:
        s.year_verified_value = str(vin_data.year)
        s.year_source = "NHTSA"
        s.year_verified = listing_data.year == vin_data.year

    # Make
    s.make_claimed = listing_data.make
    if vin_data.make is not None:
        s.make_verified_value = vin_data.make
        s.make_verified = not _make_aliases(listing_data.make).isdisjoint(_make_aliases(vin_data.make))

    # Engine
    s.engine_claimed = listing_data.engine
    if vin_data.engine_displacement is not None:
        s.engine_verified_value = f"{vin_data.engine_displacement}L ({vin_data.engine_cylinders} cyl)"
        listing_disp = normalize_displacement(listing_data.engine)
        vin_disp = normalize_displacement(vin_data.engine_displacement)
        if listing_disp is not None and vin_disp is not None:
            s.engine_verified = abs(listing_disp - vin_disp) <= 0.2

    # Color
    s.color_claimed = listing_data.color
    photo_colors = [p.visible_color for p in photo_data if p.visible_color is not None]
    if photo_colors:
        s.color_observed = max(set(photo_colors), key=photo_colors.count)
        s.color_verified = normalize_color(listing_data.color) == normalize_color(s.color_observed)

    # Mileage
    s.mileage_claimed = str(listing_data.mileage) if listing_data.mileage else None
    for photo in photo_data:
        if photo.notes and "odometer" in photo.notes.lower():
            numbers = re.findall(r'\b\d{4,6}\b', photo.notes)
            for num in numbers:
                odometer_reading = int(num)
                s.mileage_photo_read = str(odometer_reading)
                if listing_data.mileage:
                    s.mileage_consistent = abs(odometer_reading - listing_data.mileage) <= 500
                break
        if s.mileage_photo_read:
            break

    # Photos
    s.photos_analyzed = len(photo_data)
    s.photos_with_damage = sum(1 for p in photo_data if p.visible_damage)
    seen: set[str] = set()
    for p in photo_data:
        for obs in (p.visible_damage or []):
            if obs not in seen:
                seen.add(obs)
                s.damage_observations.append(obs)

    # VIN
    s.vin_decoded = vin_data.make is not None

    # Editorial
    s.editorial_score = editorial_data.completeness_score
    if editorial_data.completeness_score is not None:
        if editorial_data.completeness_score >= 0.9:
            s.editorial_score_label = "Strong"
        elif editorial_data.completeness_score >= 0.7:
            s.editorial_score_label = "Good"
        else:
            s.editorial_score_label = "Needs work"

    return s


# --- Main verification function ---
def verify_listing(
    listing_data: ListingData,
    vin_data: VINData,
    photo_data: list[PhotoAnalysis],
    editorial_data: EditorialFlags
) -> tuple[list[Flag], VerificationSummary]:
    flags = []

    # Run all checks
    checks = [
        check_make(listing_data, vin_data),
        check_year(listing_data, vin_data),
        check_engine(listing_data, vin_data),
        check_color(listing_data, photo_data),
        check_mileage_vs_odometer(listing_data, photo_data),
    ]

    for flag in checks:
        if flag is not None:
            flags.append(flag)

    # Photo angle checks return a list
    flags.extend(check_photo_angles(photo_data))

    # Editorial completeness check
    if editorial_data.completeness_score < 0.7:
        flags.append(Flag(
            field_name="editorial_completeness",
            claimed_value=None,
            verified_value=str(editorial_data.completeness_score),
            source_of_truth="editorial_agent",
            confidence=0.8,
            severity="WARNING",
            suggested_fix=f"Editorial completeness score is low ({editorial_data.completeness_score}). Review: {editorial_data.notes}"
        ))

    # Flags below 0.70 confidence produce more noise than signal — drop them
    # before presenting results to avoid overwhelming reviewers.
    flags = [f for f in flags if f.confidence >= 0.70]

    # Sort by severity (ERROR → WARNING → INFO), then confidence descending
    # within each tier so the most certain findings surface first.
    severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    flags.sort(key=lambda f: (severity_order[f.severity], -f.confidence))

    summary = build_verification_summary(listing_data, vin_data, photo_data, editorial_data)
    return flags, summary


# --- Quick test ---
if __name__ == "__main__":
    from agents.extraction_agent import ListingData
    from agents.vin_agent import VINData
    from agents.photo_agent import PhotoAnalysis
    from agents.editorial_agent import EditorialFlags

    # Simulate a listing with a deliberate year error
    listing = ListingData(
        make="Honda",
        model="S2000",
        year=2003,  # WRONG — should be 2004
        mileage=64200,
        color="Silverstone Metallic",
        engine="2.2L I4",
        transmission="manual",
        asking_price=None,
        seller_description="2004 Honda S2000 in Silverstone Metallic."
    )

    vin = VINData(
        vin="JHMAP21474T001128",
        make="HONDA",
        model="S2000",
        year=2004,  # Correct per NHTSA
        engine_displacement="2.2",
        engine_cylinders="4",
        engine_hp="240",
        fuel_type="Gasoline",
        transmission=None,
        drive_type="RWD",
        body_style="Convertible",
        plant_country="JAPAN"
    )

    photos = [
        PhotoAnalysis(
            image_url="https://example.com/photo1.jpg",
            visible_color="Silver",
            visible_damage=[],
            missing_angles=["engine bay", "undercarriage"],
            confidence_score=0.82,
            notes="Odometer reads 40751 miles."
        )
    ]

    editorial = EditorialFlags(
        highlights_text="THIS... is a 2004 Honda S2000...",
        has_consistent_voice=True,
        missing_sections=[],
        grammar_issues=[],
        completeness_score=0.95,
        notes=None
    )

    flags, summary = verify_listing(listing, vin, photos, editorial)

    print(f"Found {len(flags)} flag(s):\n")
    for flag in flags:
        print(flag.model_dump_json(indent=2))
        print()