from dotenv import load_dotenv

load_dotenv()

from agents.extraction_agent import ListingData
from agents.vin_agent import VINData
from agents.editorial_agent import EditorialFlags
from core.constants import CONFIDENCE_FLOOR, REQUIRED_PHOTO_ANGLES
from core.verifier import (
    verify_listing,
    check_engine,
    check_drivetrain,
    check_mileage_consistency,
    check_color,
    check_photo_angles,
)

# completeness_score=1.0 so the editorial-completeness check never fires --
# these tests aren't about editorial quality, and eval/eval_runner.py's own
# _STUB_EDITORIAL uses the same value for the same reason.
_STUB_EDITORIAL = EditorialFlags(
    highlights_text="",
    has_consistent_voice=True,
    missing_sections=[],
    grammar_issues=[],
    completeness_score=1.0,
    notes=None,
)


def make_listing(**overrides) -> ListingData:
    defaults = dict(
        make="Honda",
        model="Civic",
        year=2020,
        mileage=50000,
        color="Blue",
        vin="1HGCV1F34LA000000",
        engine="2.0L I4",
        transmission="automatic",
        drivetrain="FWD",
        trim=None,
        interior_color=None,
        modifications=[],
        asking_price=None,
        seller_description="",
    )
    defaults.update(overrides)
    return ListingData(**defaults)


def make_vin(**overrides) -> VINData:
    defaults = dict(
        vin="1HGCV1F34LA000000",
        make="HONDA",
        model="CIVIC",
        year=2020,
        engine_displacement="2.0",
        engine_cylinders="4",
        engine_hp="158",
        fuel_type="Gasoline",
        transmission="automatic",
        drive_type="FWD",
        body_style="Sedan",
        plant_country="USA",
    )
    defaults.update(overrides)
    return VINData(**defaults)


# --- Mileage tolerance (MILEAGE_TOLERANCE_MILES = 5000), strict `>` ---

def test_mileage_exactly_at_tolerance_does_not_flag():
    listing = make_listing(
        mileage=50000,
        seller_description="July 2024 (55,000 miles): Oil change performed.",
    )
    assert check_mileage_consistency(listing) is None


def test_mileage_one_mile_past_tolerance_flags():
    listing = make_listing(
        mileage=50000,
        seller_description="July 2024 (55,001 miles): Oil change performed.",
    )
    flag = check_mileage_consistency(listing)
    assert flag is not None
    assert flag.field_name == "mileage"
    assert flag.severity == "WARNING"


# --- Engine displacement tolerance (ENGINE_DISPLACEMENT_TOLERANCE = 0.2), strict `>` ---
# normalize_displacement() rounds every value to one decimal place, so 0.3L
# (not 0.2001L) is the smallest gap actually representable past the 0.2L line.
#
# NOTE: floating-point subtraction makes "exactly 0.2" unstable depending on
# which decimal values are used -- e.g. 2.2 - 2.0 computes to
# 0.20000000000000018 (flags), while 2.0 - 1.8 computes to
# 0.19999999999999996 (doesn't flag), for the same conceptual 0.2L gap. This
# test uses the pair that lands on the "doesn't flag" side of that float
# noise; it does not mean every 0.2L-apart pair behaves identically.

def test_engine_displacement_exactly_at_tolerance_does_not_flag():
    listing = make_listing(engine="2.0L I4")
    vin = make_vin(engine_displacement="1.8")
    assert check_engine(listing, vin) is None


def test_engine_displacement_past_tolerance_flags():
    listing = make_listing(engine="2.3L I4")
    vin = make_vin(engine_displacement="2.0")
    flag = check_engine(listing, vin)
    assert flag is not None
    assert flag.field_name == "engine_displacement"
    assert flag.severity == "WARNING"


# --- Confidence floor (CONFIDENCE_FLOOR = 0.70), filter inside verify_listing uses `>=` ---

def test_awd_4wd_mismatch_sits_exactly_at_floor_and_survives_filtering():
    listing = make_listing(drivetrain="AWD")
    vin = make_vin(drive_type="4WD")

    flag = check_drivetrain(listing, vin)
    assert flag is not None
    assert flag.confidence == CONFIDENCE_FLOOR

    flags, _ = verify_listing(listing, vin, [], _STUB_EDITORIAL)
    drivetrain_flags = [f for f in flags if f.field_name == "drivetrain"]
    assert len(drivetrain_flags) == 1, (
        "a flag exactly at CONFIDENCE_FLOOR must survive the >= filter, "
        "not be silently dropped the way the smooth-confidence regression was"
    )


def test_non_awd_4wd_mismatch_is_not_floored():
    listing = make_listing(drivetrain="FWD")
    vin = make_vin(drive_type="AWD")
    flag = check_drivetrain(listing, vin)
    assert flag is not None
    assert flag.confidence == 0.9


# --- Missing VIN data ---

def test_decode_error_produces_vin_verification_flag_not_a_crash():
    listing = make_listing()
    vin = make_vin(decode_error="NHTSA request failed", pre_standard_vin=False)
    flags, _ = verify_listing(listing, vin, [], _STUB_EDITORIAL)
    vin_flags = [f for f in flags if f.field_name == "vin_verification"]
    assert len(vin_flags) == 1
    assert vin_flags[0].severity == "WARNING"


def test_pre_standard_vin_produces_info_flag_not_a_warning():
    listing = make_listing()
    vin = make_vin(decode_error="VIN too short to decode", pre_standard_vin=True)
    flags, _ = verify_listing(listing, vin, [], _STUB_EDITORIAL)
    vin_flags = [f for f in flags if f.field_name == "vin_pre_standard_era"]
    assert len(vin_flags) == 1
    assert vin_flags[0].severity == "INFO"


def test_single_missing_vin_field_returns_info_flag_not_a_crash():
    listing = make_listing()
    vin = make_vin(engine_displacement=None)
    flag = check_engine(listing, vin)
    assert flag is not None
    assert flag.severity == "INFO"
    assert flag.confidence == 0.4


# --- Zero photos ---

def test_zero_photos_adds_photo_verification_flag():
    listing = make_listing()
    vin = make_vin()
    flags, _ = verify_listing(listing, vin, [], _STUB_EDITORIAL)
    photo_flags = [f for f in flags if f.field_name == "photo_verification"]
    assert len(photo_flags) == 1
    assert photo_flags[0].severity == "WARNING"
    assert photo_flags[0].confidence == 0.9


def test_zero_photos_color_check_returns_info_not_a_crash():
    listing = make_listing(color="Blue")
    flag = check_color(listing, [])
    assert flag is not None
    assert flag.severity == "INFO"
    assert flag.confidence == 0.3


def test_zero_photos_every_required_angle_reported_missing_at_ceiling_confidence():
    flags = check_photo_angles([])
    assert len(flags) == len(REQUIRED_PHOTO_ANGLES)
    assert all(f.confidence == 0.95 for f in flags)
