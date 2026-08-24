from pydantic import BaseModel
from typing import Optional, Literal
import re
from agents.extraction_agent import ListingData
from agents.vin_agent import VINData
from agents.photo_agent import PhotoAnalysis
from agents.editorial_agent import EditorialFlags
from core.constants import (
    REQUIRED_PHOTO_ANGLES,
    MANUFACTURER_ALIASES,
    CONFIDENCE_FLOOR,
    ENGINE_DISPLACEMENT_TOLERANCE,
    MILEAGE_TOLERANCE_MILES,
    COLOR_MISMATCH_MAJORITY,
    DUPLICATE_PHOTO_HASH_DISTANCE,
)


class Flag(BaseModel):
    field_name: str
    claimed_value: Optional[str]
    verified_value: Optional[str]
    source_of_truth: str
    confidence: float  # 0.0 to 1.0
    severity: Literal["ERROR", "WARNING", "INFO"]
    suggested_fix: str


class FlagWithFloorStatus(BaseModel):
    """Pairs a Flag with whether it cleared CONFIDENCE_FLOOR at the time
    verify_listing() ran -- floor status is a property of a specific run's
    threshold, not something inherent to the flag itself, so it's kept
    separate rather than added directly onto Flag."""
    flag: Flag
    meets_confidence_floor: bool


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
    mileage_checkpoint: Optional[str] = None
    mileage_consistent: Optional[bool] = None

    photos_analyzed: int = 0
    photos_with_damage: int = 0
    damage_observations: list[str] = []

    vin_decoded: bool = False
    vin_source: str = "NHTSA"

    editorial_score: Optional[float] = None
    editorial_score_label: Optional[str] = None

    # Every flag verify_listing() computed before CONFIDENCE_FLOOR
    # filtering, each tagged with whether it cleared the floor -- without
    # this, a future threshold-sensitivity analysis could only ever
    # simulate RAISING the floor above whatever it currently is (among
    # flags that already survived it), never lowering it to recover
    # signal that got suppressed, which is usually the more interesting
    # direction. Populated in verify_listing() right before its existing
    # floor-filter step.
    all_flags_before_floor: list[FlagWithFloorStatus] = []


# --- Normalization helpers ---
def normalize_color(color: Optional[str]) -> Optional[str]:
    if not color:
        return None
    color = color.lower().strip()
    base_colors = ["black", "white", "silver", "gray", "grey", "red", "blue",
                   "green", "yellow", "orange", "brown", "purple", "gold", "beige"]
    # Real color descriptions (both listing text and vision output) put the
    # primary exterior color first and secondary colors (roof, trim,
    # interior) after "with" -- e.g. "white with a black Targa roof" (seen
    # on a real listing this session). Without checking this segment first,
    # "black" (checked before "white" purely because of base_colors' fixed
    # order) would win regardless of which color is actually the body color.
    primary_segment = re.split(r"\bwith\b", color, maxsplit=1)[0]
    words = re.findall(r"[a-z]+", primary_segment)
    for base in base_colors:
        if base in words:
            return base
    # Fall back to the full string if nothing recognized before "with".
    words = re.findall(r"[a-z]+", color)
    for base in base_colors:
        if base in words:
            return base
    # Unrecognized/exotic manufacturer name (e.g. Porsche's "Chalk") -- see
    # check_color, which treats None as "can't reliably compare" rather
    # than falling back to the raw string, which would never match a plain
    # base-color word from vision and would guarantee a false mismatch.
    return None


def normalize_transmission(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.lower().strip()
    # Automated-manual-style gearboxes (AMT, DCT/DSG, PDK) have no clutch
    # pedal and are universally marketed and driven as automatics, even
    # though NHTSA's raw "Transmission Style" field can literally contain
    # the word "manual" (e.g. "Automated Manual Transmission (AMT)", seen
    # on a real Porsche PDK-equipped VIN this session) -- checked before the
    # generic "manual" substring match below, or every dual-clutch car gets
    # misclassified as manual.
    if any(tok in value for tok in ["automated manual", "dual-clutch", "dual clutch", "dct", "pdk", "dsg"]):
        return "automatic"
    if "manual" in value or "standard" in value:
        return "manual"
    if "automatic" in value or "automated" in value:
        return "automatic"
    if "cvt" in value:
        return "cvt"
    return value


def normalize_drivetrain(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.lower().strip()
    # NHTSA's "Drive Type" field is verbose (e.g. "4WD/4-Wheel Drive/4x4");
    # listing text is usually already terse ("RWD", "Rear-wheel drive").
    # Check 4WD before AWD/RWD/FWD since some raw strings contain both
    # "4x4" and unrelated substrings that could otherwise mis-match.
    if any(tok in value for tok in ["4wd", "4x4", "four-wheel", "four wheel"]):
        return "4WD"
    # NHTSA's "4x2" means 2WD, axle unspecified -- unambiguously not
    # 4WD/AWD, but can't tell FWD from RWD from this value alone. Doesn't
    # collide with any token checked below, so placement here is safe. See
    # check_drivetrain's 2WD handling for how this bucket's ambiguity is
    # resolved (flags 4WD/AWD claims, stays silent on FWD/RWD claims).
    if "4x2" in value:
        return "2WD"
    if any(tok in value for tok in ["awd", "all-wheel", "all wheel"]):
        return "AWD"
    if any(tok in value for tok in ["fwd", "front-wheel", "front wheel"]):
        return "FWD"
    if any(tok in value for tok in ["rwd", "rear-wheel", "rear wheel"]):
        return "RWD"
    return None


def normalize_displacement(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    # Prefer an explicit liter figure -- the number immediately before an
    # "L"/"-liter" unit marker, not every digit anywhere in the string. A
    # naive full-string digit-strip would concatenate a trailing
    # cylinder-count digit onto the decimal (e.g. "3.0L Turbocharged Flat-6"
    # -> "3.06" -> rounds to 3.1, not 3.0) -- a real, systematic +0.1L bias
    # on every 6/8-cylinder engine string, silently eroding
    # ENGINE_DISPLACEMENT_TOLERANCE.
    liter_match = re.search(r"(\d+\.?\d*)\s*-?\s*[Ll](?:iter)?\b", value)
    if liter_match:
        try:
            return round(float(liter_match.group(1)), 1)
        except ValueError:
            pass
    # cc figure (common on JDM/import/classic listings, e.g. "1998cc") --
    # convert to liters. Without this, a naive digit-strip on "1998cc" would
    # produce 1998.0L instead of 2.0L, off by three orders of magnitude.
    cc_match = re.search(r"(\d{3,5})\s*cc\b", value, re.IGNORECASE)
    if cc_match:
        try:
            return round(int(cc_match.group(1)) / 1000, 1)
        except ValueError:
            pass
    # Bare numeric field with no unit suffix (NHTSA's raw displacement
    # field, e.g. "1.984000") -- the whole string, once stripped, IS just
    # the number, so no leading-token extraction is needed here.
    cleaned = value.strip()
    if re.fullmatch(r"\d+\.?\d*", cleaned):
        try:
            return round(float(cleaned), 1)
        except ValueError:
            pass
    return None


def normalize_cylinders(value: Optional[str]) -> Optional[int]:
    """Extract a cylinder count from either a free-text engine description
    (e.g. "3.2L I6", "1.3L Twin-Rotor Rotary" -> None, rotary has no cylinder
    count in the usual sense) or NHTSA's numeric "Engine Number of Cylinders"
    field."""
    if not value:
        return None
    # Prefer an explicit "V6"/"I6"/"L4"-style token over a bare number, since
    # a bare number could be a displacement or horsepower fragment instead.
    engine_config_match = re.search(r"\b[VIL](\d{1,2})\b", value, re.IGNORECASE)
    if engine_config_match:
        return int(engine_config_match.group(1))
    # Flat/boxer configurations (Porsche, Subaru) don't use the V/I/L prefix
    # convention -- without this, check_engine_cylinders is silently
    # non-functional for every boxer-engine car, including real makes
    # already in this project's corpus.
    flat_match = re.search(r"\bflat[\s-]?(\d{1,2})\b", value, re.IGNORECASE)
    if flat_match:
        return int(flat_match.group(1))
    if value.strip().isdigit():
        return int(value.strip())
    return None


# --- Confidence helpers -----------------------------------------------
# Every check below used to hardcode one fixed confidence number regardless
# of how strong the underlying evidence actually was -- a mileage listing
# 5,001 miles over its tolerance line and one 17,000 miles over both
# reported the identical 0.85. These two helpers replace that with a
# confidence that varies smoothly with real evidence the checks already
# compute, at zero extra cost (no new API calls, no new data -- see
# DATA_SCIENCE_RESULTS.md's discussion of this with Ariel, 2026-08-19).
def _scaled_confidence(excess_ratio: float, floor: float, ceiling: float) -> float:
    """Scales linearly from `floor` (excess_ratio<=0, i.e. barely past the
    relevant tolerance/threshold line) up to `ceiling` (excess_ratio>=1,
    i.e. twice the tolerance past the line or more -- saturates rather
    than growing unboundedly for extreme cases)."""
    ratio = min(1.0, max(0.0, excess_ratio))
    return round(floor + (ceiling - floor) * ratio, 4)


def _avg_photo_confidence(photos: list[PhotoAnalysis]) -> float:
    """Mean of photo_agent's own per-photo confidence_score -- a signal
    this project already pays for and computes on every real run, but
    previously discarded downstream (check_color/check_photo_angles both
    hardcoded a fixed confidence regardless of what the vision model
    itself reported). Returns 1.0 (a neutral multiplier) when there are no
    photos to average, so callers that multiply by this value fall back to
    their own unscaled base confidence rather than crashing on an empty
    list."""
    if not photos:
        return 1.0
    return sum(p.confidence_score for p in photos) / len(photos)


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


def _disclosed_modification(modifications: list[str], keywords: list[str]) -> bool:
    """True if any disclosed modification mentions one of the given
    keywords -- used to avoid flagging an honestly-disclosed engine swap or
    drivetrain conversion as a listing/VIN mismatch. Cars & Bids
    specifically features many such builds (a real "5.7L Hemi V8 Engine
    Swap" listing was seen in this project's own scraped data); without
    this, the verifier would cry wolf on exactly the sellers being most
    transparent about a real modification."""
    if not modifications:
        return False
    text = " ".join(modifications).lower()
    return any(kw in text for kw in keywords)


_ENGINE_SWAP_KEYWORDS = ["engine swap", "swapped engine", "engine conversion", "motor swap", "swapped motor"]
_DRIVETRAIN_CONVERSION_KEYWORDS = ["drivetrain conversion", "awd conversion", "4wd conversion", "swapped to", "conversion to"]


def check_engine(listing: ListingData, vin: VINData) -> Optional[Flag]:
    if _disclosed_modification(listing.modifications, _ENGINE_SWAP_KEYWORDS):
        return None
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

    displacement_gap = abs(listing_displacement - vin_displacement)
    if displacement_gap > ENGINE_DISPLACEMENT_TOLERANCE:
        # Scales with how far past ENGINE_DISPLACEMENT_TOLERANCE the gap
        # is, instead of a flat 0.85 regardless of magnitude -- a 0.25L gap
        # (barely past the 0.2L tolerance) is real evidence but much
        # weaker than a 1.2L gap. Note: this eval's own injector
        # (eval/inject_real_errors.py) only ever tests ±0.7L/±1.0L offsets
        # -- always 3.5-5x past tolerance -- so today's real eval corpus
        # will mostly saturate to the ceiling here regardless; the low end
        # of this scale only shows up on genuinely near-boundary real
        # listings, which the eval doesn't currently exercise (see
        # DATA_SCIENCE_DEEP_DIVE.md proposal #3, not yet built).
        excess_ratio = (displacement_gap - ENGINE_DISPLACEMENT_TOLERANCE) / ENGINE_DISPLACEMENT_TOLERANCE
        return Flag(
            field_name="engine_displacement",
            claimed_value=listing.engine,
            verified_value=f"{vin.engine_displacement}L ({vin.engine_cylinders} cylinders)",
            source_of_truth="NHTSA",
            confidence=_scaled_confidence(excess_ratio, floor=CONFIDENCE_FLOOR, ceiling=0.95),
            severity="WARNING",
            suggested_fix=f"Listing engine ({listing.engine}) doesn't match NHTSA displacement ({vin.engine_displacement}L). Verify engine spec."
        )
    return None


def check_engine_cylinders(listing: ListingData, vin: VINData) -> Optional[Flag]:
    """Separate from check_engine's displacement comparison — a wrong
    cylinder count (e.g. claimed I6, VIN decodes to V8) is a different
    failure mode with a different fix, so it gets its own flag rather than
    being folded into the displacement flag's wording."""
    if _disclosed_modification(listing.modifications, _ENGINE_SWAP_KEYWORDS):
        return None
    if vin.engine_cylinders is None:
        return None

    listing_cylinders = normalize_cylinders(listing.engine)
    vin_cylinders = normalize_cylinders(vin.engine_cylinders)

    if listing_cylinders is None or vin_cylinders is None:
        return None

    if listing_cylinders != vin_cylinders:
        # No existing tolerance constant here (any cylinder-count mismatch
        # is meaningful, unlike displacement's 0.2L noise margin) -- but a
        # 1-cylinder gap (rare; usually a parsing quirk) is still weaker
        # evidence than a 2+ cylinder gap (e.g. I4 claimed vs V6 decoded --
        # an unambiguous real mismatch). Scales up to the ceiling at a
        # 2-cylinder gap rather than growing further, since gaps that size
        # are already unambiguous.
        cylinder_gap = abs(listing_cylinders - vin_cylinders)
        excess_ratio = (cylinder_gap - 1) / 1
        return Flag(
            field_name="engine_cylinders",
            claimed_value=listing.engine,
            verified_value=f"{vin.engine_cylinders} cylinders",
            source_of_truth="NHTSA",
            confidence=_scaled_confidence(excess_ratio, floor=CONFIDENCE_FLOOR, ceiling=0.90),
            severity="WARNING",
            suggested_fix=f"Listing implies {listing_cylinders} cylinders ({listing.engine}) but NHTSA decodes {vin_cylinders} cylinders. Verify engine spec."
        )
    return None


def check_color(listing: ListingData, photos: list[PhotoAnalysis]) -> Optional[Flag]:
    # Deliberately NOT blended with photo_agent's per-photo confidence_score,
    # unlike check_photo_angles below. That was tried (see git history /
    # DATA_SCIENCE_RESULTS.md's "smooth confidence" discussion) and measured
    # to make calibration WORSE (Brier 0.2936 -> 0.3835 via
    # analysis/confidence_scaling_validation.py), zero regressions from the
    # floor issue aside. Root cause: vision confidence_score reflects "how
    # well could I see/read the color in this photo," not "is this really a
    # mismatch" -- real color mismatches and false-alarm ones (e.g. two-tone
    # paint, odd lighting, a misread trim panel) both get similarly high
    # vision confidence, so blending it in doesn't separate them at all; it
    # just uniformly inflates the number, widening the gap between stated
    # confidence and actual accuracy instead of closing it. Left as a flat
    # constant on purpose, not an oversight -- proven not to help here, even
    # though the same technique measurably improved check_photo_angles.
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
    if listing_color_normalized is None:
        # The claimed color didn't map to any recognized base color (an
        # exotic/manufacturer-specific name like Porsche's "Chalk") -- skip
        # rather than compare it against photo_colors, which are always
        # plain base words. Comparing an exotic string against "white"/
        # "gray"/etc. would never match and would guarantee a false
        # mismatch on every such listing, not flag a real one.
        return None
    mismatches = [c for c in photo_colors if c != listing_color_normalized]

    if len(mismatches) >= len(photo_colors) * COLOR_MISMATCH_MAJORITY:
        most_common = max(set(photo_colors), key=photo_colors.count)
        return Flag(
            field_name="color",
            claimed_value=listing.color,
            verified_value=most_common,
            source_of_truth="photo_agent",
            confidence=0.75,
            severity="WARNING",
            suggested_fix=f"Listed color ({listing.color}) may not match photos. Photo agent observed '{most_common}'. Verify exterior color."
        )
    return None


def check_photo_angles(photos: list[PhotoAnalysis]) -> list[Flag]:
    flags = []
    required_angles = REQUIRED_PHOTO_ANGLES

    covered_angles = set()
    for photo in photos:
        # Infer present angles: any required angle not listed as missing in
        # this photo. Skip this inference entirely when a photo's own
        # missing_angles list is empty -- each photo is analyzed
        # independently with no visibility into the rest of the set, so an
        # empty list only means "this one photo found nothing to flag,"
        # not "the full required set is covered." Trusting it as blanket
        # coverage evidence lets a single narrow shot (e.g. a tire
        # close-up that isn't judging the whole gallery) silently override
        # every other photo's correctly-reported gaps -- found via a real
        # listing in the M7 eval checkpoint, not a hypothetical.
        photo_missing = {a.lower() for a in photo.missing_angles}
        if photo_missing:
            for angle in required_angles:
                if angle not in photo_missing:
                    covered_angles.add(angle)
        # NOTE: a prior version also scanned photo.notes for a literal
        # substring match against each required angle's name (e.g. "engine
        # bay" appearing anywhere in notes marked it covered). Removed --
        # that scan was both negation-blind (notes saying "no undercarriage
        # view in this shot" still substring-matched "undercarriage" and
        # marked it covered) and context-blind (short common angle words
        # like "front"/"rear"/"wheels and tires" appear constantly in
        # unrelated damage descriptions regardless of what the photo
        # actually shows, e.g. "no visible front-end damage" on an
        # engine-bay photo). missing_angles is the reliable signal; this
        # fallback only ever introduced false "covered" results.

    confirmed_missing = [a for a in required_angles if a not in covered_angles]

    # Scales with how reliable the vision analysis was overall across this
    # listing's photo set -- computed once, not per-angle, since "is this
    # angle really missing" depends on the whole set's analysis quality,
    # not any single photo. Additive blend (floor=CONFIDENCE_FLOOR,
    # ceiling=0.95), not a multiplier -- see the identical note in
    # check_color above; a multiplicative 0.75 * avg_confidence could drop
    # below CONFIDENCE_FLOOR whenever any real photo analysis was involved
    # (confirmed to silently drop real catches). When there are no photos
    # at all, _avg_photo_confidence returns 1.0 (maps to the ceiling) --
    # reasonable here specifically, since zero photos means every angle is
    # unambiguously, factually missing, not a case of genuine uncertainty.
    angle_confidence = _scaled_confidence(_avg_photo_confidence(photos), floor=CONFIDENCE_FLOOR, ceiling=0.95)

    for angle in confirmed_missing:
        severity = "WARNING" if angle in ["engine bay", "undercarriage"] else "INFO"
        flags.append(Flag(
            field_name="photo_angles",
            claimed_value=None,
            verified_value=None,
            source_of_truth="photo_agent",
            confidence=angle_confidence,
            severity=severity,
            suggested_fix=f"Standard photo angle missing: '{angle}'. Request this photo from the seller."
        ))

    return flags


def _normalize_make_string(make: str) -> str:
    """Strips spacing/hyphenation so 'Mercedes-Benz' and 'Mercedes Benz' (or
    whatever spacing/hyphenation convention NHTSA happens to use) compare
    equal. check_make previously relied on exact lowercased string equality,
    untested against compound-name brands -- Mercedes-Benz, Land Rover,
    Rolls-Royce, Alfa Romeo, Aston Martin are all confirmed present in the
    real 443-listing corpus but none appeared in the 19-listing checkpoint
    sample. This only handles formatting differences, not NHTSA returning
    an entirely different name with extra words -- that's a real alias-table
    gap to add only once actually observed, not guessed at."""
    return re.sub(r"[\s\-]+", "", make.lower().strip())


def _make_aliases(make: str) -> set[str]:
    normalized = make.lower().strip()
    aliases = MANUFACTURER_ALIASES.get(normalized, [normalized])
    return {_normalize_make_string(a) for a in aliases}


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


def check_drivetrain(listing: ListingData, vin: VINData) -> Optional[Flag]:
    if _disclosed_modification(listing.modifications, _DRIVETRAIN_CONVERSION_KEYWORDS):
        return None
    if vin.drive_type is None:
        return Flag(
            field_name="drivetrain",
            claimed_value=listing.drivetrain,
            verified_value=None,
            source_of_truth="NHTSA",
            confidence=0.4,
            severity="INFO",
            suggested_fix="NHTSA did not return a drive type. Verify manually."
        )

    listing_drivetrain = normalize_drivetrain(listing.drivetrain)
    vin_drivetrain = normalize_drivetrain(vin.drive_type)

    if listing_drivetrain is None or vin_drivetrain is None:
        return None

    mismatch = listing_drivetrain != vin_drivetrain
    # "4x2" (VIN-decoded "2WD") is genuinely ambiguous between FWD/RWD --
    # NHTSA gives no axle info, so a listing claiming FWD or RWD against a
    # 2WD-decoded VIN is not a real mismatch signal and must not be flagged.
    # A listing claiming 4WD or AWD against a 2WD-decoded VIN IS a real
    # mismatch and falls through to the comparison above unchanged.
    if vin_drivetrain == "2WD" and listing_drivetrain in ("FWD", "RWD"):
        mismatch = False

    if mismatch:
        # Not every mismatched pair is equally trustworthy. Of the 32 times
        # this check has ever fired across the real eval corpus, every
        # single false alarm (12 of 12) was a listing/VIN pair confusing
        # AWD with 4WD -- sellers and even NHTSA's own data use those two
        # terms loosely for what's mechanically a similar system. Every
        # other pair this check has ever seen (2WD<->4WD, 2WD<->AWD,
        # AWD<->FWD, 4WD<->FWD, AWD<->RWD) was correct 100% of the time (20
        # for 20). Floored, not dropped: 5 of the 20 real drivetrain_swap
        # catches are themselves AWD<->4WD, so scoring this pair below
        # CONFIDENCE_FLOOR would silently lose those real catches too, the
        # same mistake the smooth-confidence floor regression made before
        # (see DATA_SCIENCE_RESULTS.md section 8).
        ambiguous_pair = {listing_drivetrain, vin_drivetrain} == {"AWD", "4WD"}
        return Flag(
            field_name="drivetrain",
            claimed_value=listing.drivetrain,
            verified_value=vin.drive_type,
            source_of_truth="NHTSA",
            confidence=CONFIDENCE_FLOOR if ambiguous_pair else 0.9,
            severity="ERROR",
            suggested_fix=f"Listing claims {listing_drivetrain} but VIN decodes to {vin_drivetrain} ({vin.drive_type}). Verify drivetrain."
        )
    return None


def check_transmission(listing: ListingData, vin: VINData) -> Optional[Flag]:
    if vin.transmission is None:
        return None  # NHTSA's Transmission Style field is sparse; no data means no flag, not an INFO

    listing_transmission = normalize_transmission(listing.transmission)
    vin_transmission = normalize_transmission(vin.transmission)

    if listing_transmission is None or vin_transmission is None:
        return None

    if listing_transmission != vin_transmission:
        return Flag(
            field_name="transmission",
            claimed_value=listing.transmission,
            verified_value=vin.transmission,
            source_of_truth="NHTSA",
            confidence=0.8,
            severity="WARNING",
            suggested_fix=f"Listing claims {listing_transmission} transmission but VIN decodes to {vin_transmission} ({vin.transmission}). Verify transmission."
        )
    return None


# Matches a Carfax-style dated service-history checkpoint as it appears in
# a real Cars & Bids seller_description, e.g. "July 2026 (19,449 miles):
# Two tires replaced, wheel(s) repaired" -- a highly specific structural
# pattern (date + parenthesized mileage + colon-led service description),
# not a bare "N miles" scan, which would false-positive on unrelated
# numbers (prices, VIN fragments, "within 50 miles of the buyer"). Shared
# by check_mileage_consistency below and eval/inject_real_errors.py's
# inject_mileage_drift, so ground-truth generation and detection can never
# drift apart -- both read this exact same pattern.
_CARFAX_CHECKPOINT_RE = re.compile(
    r"\b([A-Z][a-z]+) (\d{4})\s*\((\d{1,3}(?:,\d{3})*)\s*miles?\)\s*:"
)
_MONTHS = {m: i for i, m in enumerate([
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
], 1)}
_MONTHS_BY_INDEX = {v: k for k, v in _MONTHS.items()}


def extract_carfax_checkpoints(seller_description: str) -> list[tuple[int, int, int]]:
    """Returns every (year, month, mileage) checkpoint found in the prose,
    in no particular order -- caller decides how to use them (e.g. most
    recent by date)."""
    checkpoints = []
    for month_name, year, miles in _CARFAX_CHECKPOINT_RE.findall(seller_description or ""):
        if month_name not in _MONTHS:
            continue
        checkpoints.append((int(year), _MONTHS[month_name], int(miles.replace(",", ""))))
    return checkpoints


def check_mileage_consistency(listing: ListingData) -> Optional[Flag]:
    """Cross-checks the listing's claimed current mileage against the most
    recently *dated* Carfax-style checkpoint in its own seller_description
    -- not the highest checkpoint value seen. Real listings can contain a
    genuinely out-of-order high checkpoint (e.g. an odometer/instrument
    cluster replacement disclosed earlier in the vehicle's history) without
    that being a mileage-fraud signal; measured directly against 359 real
    checkpointed listings in the eval corpus, taking the highest checkpoint
    value produced one confirmed false positive from exactly this pattern,
    while taking the most-recent-by-date checkpoint produced zero. Mileage
    only increases over a vehicle's life, so a documented recent reading
    that's *higher* than what's currently claimed -- beyond
    MILEAGE_TOLERANCE_MILES -- is specifically the odometer-rollback/
    understatement pattern this check exists to catch. Returns None (no
    signal, not "consistent") when the description has no parseable
    checkpoint at all -- honestly reflects that this check, like every
    check in this file, can't fire on every listing."""
    if listing.mileage is None:
        return None
    checkpoints = extract_carfax_checkpoints(listing.seller_description)
    if not checkpoints:
        return None
    latest_year, latest_month, latest_mileage = max(checkpoints, key=lambda c: (c[0], c[1]))
    if latest_mileage > listing.mileage + MILEAGE_TOLERANCE_MILES:
        # Scales with how far past MILEAGE_TOLERANCE_MILES the drift is,
        # instead of a flat 0.85 regardless of magnitude -- a checkpoint
        # 5,001 miles over the line is real evidence but much weaker than
        # one 17,000 miles over it.
        excess_ratio = (latest_mileage - listing.mileage - MILEAGE_TOLERANCE_MILES) / MILEAGE_TOLERANCE_MILES
        return Flag(
            field_name="mileage",
            claimed_value=str(listing.mileage),
            verified_value=str(latest_mileage),
            source_of_truth="seller_description",
            confidence=_scaled_confidence(excess_ratio, floor=CONFIDENCE_FLOOR, ceiling=0.95),
            severity="WARNING",
            suggested_fix=f"Listed mileage ({listing.mileage}) is lower than a documented service record showing {latest_mileage} miles ({_MONTHS_BY_INDEX[latest_month]} {latest_year}). Verify current mileage."
        )
    return None


def check_duplicate_photos(duplicate_pairs: list[tuple[str, str, int]]) -> list[Flag]:
    """duplicate_pairs is the output of agents.photo_agent.detect_duplicate_photos:
    (url_a, url_b, hamming_distance) for any pair of photos perceptually close
    enough to be the same or a reused image."""
    flags = []
    for url_a, url_b, distance in duplicate_pairs:
        # Inverted scale: distance=0 (pixel-identical) is near-certain, a
        # distance right at DUPLICATE_PHOTO_HASH_DISTANCE (the threshold
        # detect_duplicate_photos used to include this pair at all) is
        # much weaker, borderline evidence -- previously both reported the
        # identical flat 0.75.
        excess_ratio = 1 - (distance / DUPLICATE_PHOTO_HASH_DISTANCE)
        flags.append(Flag(
            field_name="duplicate_photos",
            claimed_value=None,
            verified_value=f"hamming distance {distance}",
            source_of_truth="photo_agent",
            confidence=_scaled_confidence(excess_ratio, floor=CONFIDENCE_FLOOR, ceiling=0.95),
            severity="WARNING",
            suggested_fix=f"Photos appear to be duplicates or reused images: {url_a} and {url_b}. Verify these are distinct, current photos of this car."
        ))
    return flags


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

    # Engine -- stays unset (None, "not verified") rather than a hard
    # True/False when a disclosed modification means check_engine itself
    # skips producing a flag, so this summary panel never contradicts the
    # actual flags/report shown right next to it (a real inconsistency:
    # without this, a disclosed engine swap would correctly suppress the
    # WARNING flag while this separate summary still showed "Mismatch").
    s.engine_claimed = listing_data.engine
    if vin_data.engine_displacement is not None and not _disclosed_modification(listing_data.modifications, _ENGINE_SWAP_KEYWORDS):
        s.engine_verified_value = f"{vin_data.engine_displacement}L ({vin_data.engine_cylinders} cyl)"
        listing_disp = normalize_displacement(listing_data.engine)
        vin_disp = normalize_displacement(vin_data.engine_displacement)
        if listing_disp is not None and vin_disp is not None:
            s.engine_verified = abs(listing_disp - vin_disp) <= ENGINE_DISPLACEMENT_TOLERANCE

    # Color -- same "stays unset rather than False" reasoning: if the
    # claimed color is an exotic/manufacturer-specific name with no
    # recognized base word, check_color itself skips rather than
    # guaranteeing a false mismatch (see normalize_color/check_color); this
    # summary needs the same skip or it would show "Mismatch" for a
    # listing the flags list correctly says nothing about.
    s.color_claimed = listing_data.color
    photo_colors = [p.visible_color for p in photo_data if p.visible_color is not None]
    if photo_colors:
        s.color_observed = max(set(photo_colors), key=photo_colors.count)
        if normalize_color(listing_data.color) is not None:
            s.color_verified = normalize_color(listing_data.color) == normalize_color(s.color_observed)

    # Mileage
    s.mileage_claimed = str(listing_data.mileage) if listing_data.mileage else None
    checkpoints = extract_carfax_checkpoints(listing_data.seller_description)
    if checkpoints and listing_data.mileage is not None:
        latest_mileage = max(checkpoints, key=lambda c: (c[0], c[1]))[2]
        s.mileage_checkpoint = str(latest_mileage)
        s.mileage_consistent = latest_mileage <= listing_data.mileage + MILEAGE_TOLERANCE_MILES

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
    editorial_data: EditorialFlags,
    duplicate_photo_pairs: Optional[list[tuple[str, str, int]]] = None,
) -> tuple[list[Flag], VerificationSummary]:
    flags = []

    # Run all checks
    checks = [
        check_make(listing_data, vin_data),
        check_year(listing_data, vin_data),
        check_engine(listing_data, vin_data),
        check_engine_cylinders(listing_data, vin_data),
        check_drivetrain(listing_data, vin_data),
        check_transmission(listing_data, vin_data),
        check_color(listing_data, photo_data),
        check_mileage_consistency(listing_data),
    ]

    for flag in checks:
        if flag is not None:
            flags.append(flag)

    # Photo angle checks return a list
    flags.extend(check_photo_angles(photo_data))

    # Duplicate/reused photo checks return a list
    flags.extend(check_duplicate_photos(duplicate_photo_pairs or []))

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

    # Explicit "verification was skipped" flags — these sit above the
    # confidence floor deliberately. A reviewer needs to be told outright
    # that VIN/photo verification didn't happen, not left to infer it from
    # the absence of any other flag.
    if vin_data.decode_error is not None:
        if vin_data.pre_standard_vin:
            # Distinct field_name and INFO severity, deliberately not
            # WARNING: this isn't something a reviewer needs to act on or
            # something the seller did wrong -- it's an expected, honest
            # gap for any vehicle old enough to predate the 17-character
            # VIN standard. Conflating it with a genuine decode failure
            # (below) would wrongly imply an error occurred.
            flags.append(Flag(
                field_name="vin_pre_standard_era",
                claimed_value=vin_data.vin,
                verified_value=None,
                source_of_truth="NHTSA",
                confidence=0.9,
                severity="INFO",
                suggested_fix=(
                    "This VIN predates the 17-character format standardized in 1981, "
                    "so NHTSA has no decode data for it. Make/year/engine/drivetrain/"
                    "transmission could not be cross-checked because the reference "
                    "data itself doesn't exist for vehicles this old — not because "
                    "verification failed. Verify these fields manually against other "
                    "sources (e.g. a marque registry or the seller's documentation)."
                )
            ))
        else:
            flags.append(Flag(
                field_name="vin_verification",
                claimed_value=vin_data.vin,
                verified_value=None,
                source_of_truth="NHTSA",
                confidence=0.9,
                severity="WARNING",
                suggested_fix=f"VIN could not be verified against NHTSA ({vin_data.decode_error}). All VIN-based checks (make, year, engine, drivetrain, transmission) were skipped — verify these fields manually."
            ))
    if not photo_data:
        flags.append(Flag(
            field_name="photo_verification",
            claimed_value=None,
            verified_value=None,
            source_of_truth="photo_agent",
            confidence=0.9,
            severity="WARNING",
            suggested_fix="No photos were provided or analyzed. All photo-based checks (color, photo angles, duplicate photos) were skipped — verify these manually."
        ))

    # Captured before floor-filtering so callers that want it (see
    # VerificationSummary.all_flags_before_floor) can still see what got
    # suppressed, not just what survived.
    all_flags_before_floor = [
        FlagWithFloorStatus(flag=f, meets_confidence_floor=f.confidence >= CONFIDENCE_FLOOR)
        for f in flags
    ]

    # Flags below the confidence floor produce more noise than signal — drop
    # them before presenting results to avoid overwhelming reviewers.
    flags = [f for f in flags if f.confidence >= CONFIDENCE_FLOOR]

    # Sort by severity (ERROR → WARNING → INFO), then confidence descending
    # within each tier so the most certain findings surface first.
    severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    flags.sort(key=lambda f: (severity_order[f.severity], -f.confidence))

    summary = build_verification_summary(listing_data, vin_data, photo_data, editorial_data)
    summary.all_flags_before_floor = all_flags_before_floor
    return flags, summary


# --- Quick test ---
if __name__ == "__main__":
    from agents.extraction_agent import ListingData
    from agents.vin_agent import VINData
    from agents.photo_agent import PhotoAnalysis
    from agents.editorial_agent import EditorialFlags

    # Simulate a listing with a deliberate year error and a deliberate
    # drivetrain error
    listing = ListingData(
        make="Honda",
        model="S2000",
        year=2003,  # WRONG — should be 2004
        mileage=64200,
        color="Silverstone Metallic",
        vin="JHMAP21474T001128",
        engine="2.2L I4",
        transmission="manual",
        drivetrain="AWD",  # WRONG — S2000 is RWD
        trim=None,
        interior_color=None,
        modifications=[],
        asking_price=None,
        seller_description=(
            "2004 Honda S2000 in Silverstone Metallic. The attached Carfax "
            "history report shows the following services have been "
            "performed:\n\nJanuary 2024 (70,500 miles): Oil change performed."
        )
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
            notes=None
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