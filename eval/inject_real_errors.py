import argparse
import json
import random
from pathlib import Path

from agents.vin_agent import verify_vin
from core.constants import MANUFACTURER_ALIASES, MILEAGE_TOLERANCE_MILES
from core.verifier import normalize_color, normalize_cylinders, normalize_drivetrain, extract_carfax_checkpoints
from corpus.storage import get_all_detail_auction_ids, get_auction_detail

DEFAULT_OUT = Path(__file__).parent / "real_listing_ground_truth.json"

# Deliberately picks pairs that are NOT aliases of each other in
# MANUFACTURER_ALIASES (core/constants.py) -- swapping to an aliased make
# would get silently absorbed by check_make's alias check instead of
# tripping the ERROR it's supposed to test.
MAKE_SWAP = {
    "porsche": "Audi", "audi": "BMW", "bmw": "Mercedes-Benz",
    "mercedes-benz": "Audi", "honda": "Toyota", "toyota": "Honda",
    "ford": "Chevrolet", "chevrolet": "Ford", "nissan": "Mazda",
    "mazda": "Subaru", "subaru": "Nissan", "volkswagen": "Honda",
    "lexus": "Acura", "acura": "Lexus", "infiniti": "Lexus",
    "land rover": "Jeep", "jeep": "Land Rover", "dodge": "Ford",
    "tesla": "Ford", "volvo": "Audi", "jaguar": "BMW",
}

DRIVETRAIN_OPTIONS = ["RWD", "AWD", "FWD", "4WD"]

MILEAGE_DRIFT_BANDS = [6000, 10000, 15000]  # miles; all > MILEAGE_TOLERANCE_MILES (5000,
# core/constants.py) with real margin. Previously [800, 3000, 15000], set when
# the tolerance was still 500 -- once the tolerance was raised to 5000 (real
# noise-vs-signal separation measured at the time), 2 of these 3 bands (800,
# 3000) silently became mathematically uncatchable: 42 of 55 real
# mileage_drift eval rows had a drift magnitude at or below the current
# tolerance, so no detection improvement could ever have caught them. These
# bands must stay above MILEAGE_TOLERANCE_MILES with real margin, matching
# the genuine-drift-vs-noise separation already measured for that constant
# (genuine deltas 6,980-17,755mi; noise 700-4,850mi).


def _severity_to_verdict(severity: str, error_field: str) -> str:
    """Same reasoning eval_runner.py's _expected_verdict_for_row used for the
    old CSV rows: a make/year ERROR is a fraud signal (reject), any other
    ERROR or a WARNING deserves human review, INFO alone shouldn't block."""
    if severity == "ERROR":
        return "reject" if error_field in ("make", "year") else "needs_review"
    if severity == "WARNING":
        return "needs_review"
    return "approve"


def build_baseline(detail: dict) -> dict:
    """Flattens the raw scraped detail dict (corpus/scrape_listing_details.py's
    output shape) into the clean baseline fields the injectors mutate, plus a
    flat (category, url) photo list for the photo-based injectors."""
    flat_photos = [
        {"category": category, "url": p["url"]}
        for category, plist in (detail.get("photos") or {}).items()
        for p in plist
    ]
    return {
        "make": detail.get("make"),
        "model": detail.get("model"),
        "year": detail.get("year"),
        "trim": detail.get("trim"),
        "vin": detail.get("vin"),
        "mileage": detail.get("mileage"),
        "exterior_color": detail.get("exterior_color"),
        "interior_color": detail.get("interior_color"),
        "engine": detail.get("engine"),
        "transmission": detail.get("transmission"),
        "drivetrain": detail.get("drivetrain"),
        "seller_description": detail.get("seller_description"),
        "photos": flat_photos,
        # Not mutated by any injector -- carried through purely so
        # downstream eval output (eval_runner.py) can persist them for
        # future analysis (geographic/seller-type breakdowns, source
        # link-through). Already sitting in corpus.db, zero extra scraping.
        "location": detail.get("location"),
        "seller_type": detail.get("seller_type"),
        "title_status": detail.get("title_status"),
        "body_style": detail.get("body_style"),
        "url": detail.get("url"),
    }


def inject_year_error(baseline: dict, rng: random.Random) -> tuple[dict, str]:
    """check_year: any listing/VIN year mismatch is ERROR (fraud-adjacent --
    a claimed model year that doesn't match the VIN is a hard stop)."""
    real_year = baseline["year"]
    claimed = real_year + rng.choice([-1, 1])
    entry = {
        "error_type": "year_error", "error_field": "year",
        "claimed_value": str(claimed), "correct_value": str(real_year),
        "expected_flag_severity": "ERROR",
    }
    return entry, "ERROR"


def inject_make_error(baseline: dict, rng: random.Random) -> tuple[dict, str]:
    """check_make: any non-aliased make mismatch is ERROR. Skipped if make
    is missing (a rare but real scraper gap) rather than crashing on
    .lower() against None -- at 443-listing scale, an unusual real listing
    hitting an unexpected data gap is a real possibility, not hypothetical.
    Also skipped when NHTSA couldn't decode a make for this VIN at all
    (pre-1981 VINs, before the 17-char VIN format existed) -- check_make
    itself (core/verifier.py) returns None with no flag whenever
    vin.make is None, so assigning this error type to such a listing would
    be an unwinnable test by construction, same convention already used by
    inject_transmission_swap/inject_drivetrain_swap for their own VIN-data
    preconditions."""
    real_make = baseline["make"]
    if not real_make:
        return None, None
    if not (baseline.get("vin_data") or {}).get("make"):
        return None, None
    claimed = MAKE_SWAP.get(real_make.lower().strip(), "Kia")
    if claimed.lower() == real_make.lower():
        claimed = "Kia" if real_make.lower() != "kia" else "Mazda"
    entry = {
        "error_type": "make_error", "error_field": "make",
        "claimed_value": claimed, "correct_value": real_make,
        "expected_flag_severity": "ERROR",
    }
    return entry, "ERROR"


def inject_mileage_drift(baseline: dict, rng: random.Random) -> tuple[dict, str]:
    """check_mileage_consistency: WARNING if the listing's claimed mileage
    is lower than the most recently *dated* Carfax-style service checkpoint
    in its own seller_description, by more than MILEAGE_TOLERANCE_MILES.
    Skipped if mileage is missing, or if no checkpoint can be found in the
    real prose at all (~28% of real listings, measured) -- there is no
    listing-vs-VIN mileage check (mileage isn't on a VIN), so a checkpoint
    is the only real signal available, same honest-skip convention as
    inject_transmission_swap when NHTSA has no transmission data.
    Deliberately does NOT patch seller_description -- the real, unpatched
    checkpoint contradicting the mutated claimed_value *is* the signal;
    patching it out would defeat the check being tested.
    Also skipped if the baseline is already inconsistent before any
    mutation (a real, if rare, case: a genuine pre-existing Carfax
    oddity, e.g. an instrument-cluster replacement, can make a checkpoint
    legitimately exceed the real current mileage) -- injecting on top of
    an already-flaggable baseline would test nothing meaningful. Also
    skipped for very-low-mileage listings where clamping claimed_value to
    a non-negative number (max(0, ...)) would eat the tolerance margin --
    e.g. a checkpoint of only a few hundred miles can't produce a claimed
    value both >= 0 and > MILEAGE_TOLERANCE_MILES below it; injecting an
    unwinnable case there would fabricate ground truth this check could
    never pass, the same thing this function already avoids above."""
    if baseline.get("mileage") is None:
        return None, None
    checkpoints = extract_carfax_checkpoints(baseline.get("seller_description") or "")
    if not checkpoints:
        return None, None
    real_mileage = int(baseline["mileage"])
    latest_checkpoint = max(checkpoints, key=lambda c: (c[0], c[1]))[2]
    if latest_checkpoint > real_mileage + MILEAGE_TOLERANCE_MILES:
        return None, None  # baseline already inconsistent -- not a clean test case
    drift = rng.choice(MILEAGE_DRIFT_BANDS)
    claimed = max(0, latest_checkpoint - drift)
    if latest_checkpoint <= claimed + MILEAGE_TOLERANCE_MILES:
        return None, None  # clamping to 0 ate the margin -- unwinnable by construction
    entry = {
        "error_type": "mileage_drift", "error_field": "mileage",
        "claimed_value": str(claimed), "correct_value": str(real_mileage),
        "expected_flag_severity": "WARNING",
    }
    return entry, "WARNING"


def inject_transmission_swap(baseline: dict, rng: random.Random) -> tuple[dict, str]:
    """check_transmission: WARNING on a manual/automatic mismatch. Skipped
    (returns None) when NHTSA didn't return a Transmission Style for this
    real VIN -- check_transmission itself returns None with no data (not
    even a low-confidence flag) when vin.transmission is None, so assigning
    this error type to such a listing would be an unwinnable test of the
    injector's own making, not a real measurement of the pipeline."""
    if not (baseline.get("vin_data") or {}).get("transmission"):
        return None, None
    real = (baseline["transmission"] or "").lower()
    claimed = "Manual" if "auto" in real else "Automatic"
    entry = {
        "error_type": "transmission_swap", "error_field": "transmission",
        "claimed_value": claimed, "correct_value": baseline["transmission"],
        "expected_flag_severity": "WARNING",
    }
    return entry, "WARNING"


def inject_drivetrain_swap(baseline: dict, rng: random.Random) -> tuple[dict, str]:
    """check_drivetrain: ERROR on any drivetrain mismatch. Skipped (returns
    None) when NHTSA didn't return a Drive Type for this real VIN --
    check_drivetrain falls back to a low-confidence INFO flag in that case,
    which verify_listing's CONFIDENCE_FLOOR always drops, so assigning this
    error type to such a listing would be an unwinnable test by construction,
    not a real measurement of the pipeline (confirmed empirically: this is
    exactly what happened to two real listings in the first 19-listing
    checkpoint).

    DRIVETRAIN_OPTIONS's raw-string inequality against the listing's own
    drivetrain field isn't the same comparison check_drivetrain actually
    performs (normalize_drivetrain(claimed) vs normalize_drivetrain(vin
    drive_type)) -- a coincidental normalization collision could otherwise
    silently produce an uncatchable injected case. Filtered below to only
    candidates that would actually normalize to a mismatch, mirroring
    inject_mileage_drift's verify-before-accepting pattern as closely as
    possible while keeping exactly one rng.choice() call (filtering the
    candidate list before the call, not retrying after it) -- both matter
    for build_ground_truth's shared random.Random(seed) round-robin (see
    module docstring)."""
    vin_drive_type = (baseline.get("vin_data") or {}).get("drive_type")
    if not vin_drive_type:
        return None, None
    real = baseline["drivetrain"]
    vin_normalized = normalize_drivetrain(vin_drive_type)

    def _catchable(candidate: str) -> bool:
        candidate_normalized = normalize_drivetrain(candidate)
        if candidate_normalized == vin_normalized:
            return False
        # Mirrors core/verifier.py's check_drivetrain 2WD-ambiguity
        # carve-out -- FWD/RWD against a 2WD-decoded VIN ("4x2") isn't a
        # real mismatch signal.
        if vin_normalized == "2WD" and candidate_normalized in ("FWD", "RWD"):
            return False
        return True

    options = [d for d in DRIVETRAIN_OPTIONS if d.lower() != (real or "").lower() and _catchable(d)]
    if not options:
        return None, None
    claimed = rng.choice(options)
    entry = {
        "error_type": "drivetrain_swap", "error_field": "drivetrain",
        "claimed_value": claimed, "correct_value": real,
        "expected_flag_severity": "ERROR",
    }
    return entry, "ERROR"


def inject_engine_error(baseline: dict, rng: random.Random) -> tuple[dict, str]:
    """check_engine / check_engine_cylinders: WARNING on a displacement gap
    past ENGINE_DISPLACEMENT_TOLERANCE, or a cylinder-count mismatch.

    Skipped (returns None) for EVs -- Tesla/Rivian/Lucid are confirmed in
    the 443-listing corpus, and an EV's engine string (e.g. "Dual Motor
    AWD") has no displacement/cylinder figure at all, so
    normalize_displacement/normalize_cylinders both return None and neither
    check function has anything to compare -- the same unwinnable-test
    shape already fixed for inject_drivetrain_swap/inject_transmission_swap
    via the VIN-data precondition below.

    Builds the mutated string via direct regex substitution on the first
    "N.NL"-shaped token rather than round-tripping through
    normalize_displacement/find-and-replace, since this needs to target
    exactly that token regardless of how the rest of the string reads."""
    import re as _re
    real_engine = baseline["engine"] or ""
    if not (baseline.get("vin_data") or {}).get("engine_displacement"):
        return None, None
    disp_match = _re.search(r"(\d+\.\d+)\s*L", real_engine)
    cyl = normalize_cylinders(real_engine)

    if disp_match:
        disp = float(disp_match.group(1))
        new_disp = round(disp + rng.choice([-1.0, -0.7, 0.7, 1.0]), 1)
        new_disp = max(0.5, new_disp)
        claimed = real_engine[:disp_match.start(1)] + str(new_disp) + real_engine[disp_match.end(1):]
        error_field = "engine_displacement"
    elif cyl is not None:
        new_cyl = cyl + rng.choice([-2, 2])
        new_cyl = max(2, new_cyl)
        claimed = _re.sub(r"\b([VIL])\d{1,2}\b", rf"\g<1>{new_cyl}", real_engine, count=1)
        error_field = "engine_cylinders"
    else:
        claimed = f"{real_engine} (modified spec)"
        error_field = "engine_displacement"

    entry = {
        "error_type": "engine_error", "error_field": error_field,
        "claimed_value": claimed, "correct_value": real_engine,
        "expected_flag_severity": "WARNING",
    }
    return entry, "WARNING"


def inject_color_error(baseline: dict, rng: random.Random) -> tuple[dict, str]:
    """check_color: WARNING when a majority of photo-observed colors
    disagree with the claimed exterior_color. Real photos are left
    untouched -- the mismatch is real, not staged in the photo data."""
    real_color = baseline["exterior_color"] or ""
    normalized_real = normalize_color(real_color)
    base_colors = ["black", "white", "silver", "gray", "red", "blue",
                   "green", "yellow", "orange", "brown", "purple", "gold"]
    options = [c for c in base_colors if c != normalized_real]
    claimed = rng.choice(options).capitalize()
    entry = {
        "error_type": "color_error", "error_field": "color",
        "claimed_value": claimed, "correct_value": real_color,
        "expected_flag_severity": "WARNING",
    }
    return entry, "WARNING"


def inject_duplicate_photo(baseline: dict, rng: random.Random) -> tuple[dict, str]:
    """check_duplicate_photos: WARNING when detect_duplicate_photos finds a
    perceptual near-match. Appends an exact duplicate URL, so this is the
    one injector guaranteed to be geometrically detectable (hamming
    distance 0) regardless of vision-model judgment calls."""
    photos = baseline["photos"]
    if not photos:
        return None, None
    chosen = rng.choice(photos)
    entry = {
        "error_type": "duplicate_photo", "error_field": "duplicate_photos",
        "claimed_value": chosen["url"], "correct_value": None,
        "expected_flag_severity": "WARNING",
        "mutation_detail": {"action": "duplicate", "category": chosen["category"], "url": chosen["url"]},
    }
    return entry, "WARNING"


def inject_missing_angle(baseline: dict, rng: random.Random) -> tuple[dict, str]:
    """check_photo_angles: severity depends on which required angle ends up
    uncovered. Real category granularity is coarser than
    REQUIRED_PHOTO_ANGLES (see module docstring) -- dropping "mechanical"
    plausibly removes engine bay/undercarriage coverage (WARNING per
    check_photo_angles), any other category maps to an INFO-tier angle."""
    photos = baseline["photos"]
    categories = sorted({p["category"] for p in photos})
    if not categories:
        return None, None
    chosen_category = rng.choice(categories)
    severity = "WARNING" if chosen_category == "mechanical" else "INFO"
    entry = {
        "error_type": "missing_angle", "error_field": "photo_angles",
        "claimed_value": None, "correct_value": chosen_category,
        "expected_flag_severity": severity,
        "mutation_detail": {"action": "drop_category", "category": chosen_category},
    }
    return entry, severity


# Order matters for the round-robin cycle below, not for correctness --
# structured-field injectors first (carried over from the deleted CSV
# injector), then the two new field injectors this real-photo approach
# unlocks, then the two photo-list injectors that need real images to mean
# anything (impossible under the old fake-photo CSV approach).
INJECTORS = [
    inject_year_error,
    inject_make_error,
    inject_mileage_drift,
    inject_transmission_swap,
    inject_drivetrain_swap,
    inject_engine_error,
    inject_color_error,
    inject_duplicate_photo,
    inject_missing_angle,
]

# Every injector's error_type follows "inject_X" -> "X" (verified against
# each function's own entry dict above) -- used to record, per auction,
# what the round-robin position originally intended before any fallback
# reassignment, so later analysis can explain (not just observe) uneven
# error-type sample sizes.
INJECTOR_ERROR_TYPES = {fn: fn.__name__[len("inject_"):] for fn in INJECTORS}


def build_ground_truth(limit: int | None = None, seed: int = 0) -> list[dict]:
    rng = random.Random(seed)
    auction_ids = get_all_detail_auction_ids()
    if limit:
        auction_ids = auction_ids[:limit]

    ground_truth = []
    for i, auction_id in enumerate(auction_ids):
        detail = get_auction_detail(auction_id)
        baseline = build_baseline(detail)
        # Decoded once per auction (free, NHTSA) and attached to baseline so
        # inject_transmission_swap/inject_drivetrain_swap/inject_engine_error
        # can check whether the real VIN actually has the field they'd be
        # testing against, before claiming this listing -- see those
        # functions' docstrings. Skipped entirely when vin is missing (a
        # real, if rare, scraper gap) rather than wasting a call on a
        # guaranteed-garbage request.
        baseline["vin_data"] = verify_vin(baseline["vin"]).model_dump() if baseline.get("vin") else {}

        # Round-robin over injector types so every error category gets
        # roughly even coverage across the corpus, rather than leaving it to
        # chance and risking a category with zero (or nearly zero) samples.
        #
        # Every injector call below is wrapped in try/except: an injector
        # assumes its own baseline fields are present (e.g.
        # inject_make_error calls .lower() on baseline["make"] with no None
        # guard), and at 443-listing scale some scraped field being
        # unexpectedly None for an unusual real listing is a real
        # possibility, not a hypothetical -- the whole point of this audit.
        # Without this, one bad field on one listing would crash ground
        # truth generation for every remaining auction, not just skip the
        # one problem listing (same class of fragility already fixed once
        # in eval_runner.py's batch-result parsing).
        injector = INJECTORS[i % len(INJECTORS)]
        original_error_type = INJECTOR_ERROR_TYPES[injector]
        reassignment_reason = None
        try:
            result = injector(baseline, rng)
        except Exception as e:
            print(f"  {auction_id}: {injector.__name__} raised ({e}), trying next injector")
            reassignment_reason = f"{injector.__name__} raised: {e}"
            result = (None, None)
        if result[0] is None:
            if reassignment_reason is None:
                reassignment_reason = f"{injector.__name__} skipped (no photo data or unsupported by real VIN data)"
                print(f"  {auction_id}: {reassignment_reason}, trying next injector")
            for fallback in INJECTORS:
                try:
                    result = fallback(baseline, rng)
                except Exception as e:
                    print(f"  {auction_id}: {fallback.__name__} raised ({e}), trying next injector")
                    result = (None, None)
                if result[0] is not None:
                    break
        entry, severity = result
        if entry is None:
            print(f"  {auction_id}: no injector could run (no photos at all, or an unexpected data gap), skipping this auction")
            continue

        entry["auction_id"] = auction_id
        entry["expected_overall_verdict"] = _severity_to_verdict(severity, entry["error_field"])
        entry["original_error_type"] = original_error_type
        entry["reassigned"] = entry["error_type"] != original_error_type
        entry["reassignment_reason"] = reassignment_reason if entry["reassigned"] else None
        ground_truth.append(entry)

    return ground_truth


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    ground_truth = build_ground_truth(limit=args.limit, seed=args.seed)

    with open(args.out, "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"\n{len(ground_truth)} ground-truth entries written to {args.out}")
    from collections import Counter
    counts = Counter(e["error_type"] for e in ground_truth)
    for error_type, count in counts.items():
        print(f"  {error_type}: {count}")
