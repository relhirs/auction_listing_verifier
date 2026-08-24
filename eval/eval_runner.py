import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

import agents.extraction_agent as extraction_agent
import agents.photo_agent as photo_agent
import agents.synthesis_agent as synthesis_agent
from agents.vin_agent import verify_vin, VINData
from agents.photo_agent import PhotoAnalysis, detect_duplicate_photos
from agents.editorial_agent import EditorialFlags
from agents.synthesis_agent import compute_action, compute_score, NO_ISSUES_SUMMARY
from core.constants import (
    CONFIDENCE_FLOOR,
    ENGINE_DISPLACEMENT_TOLERANCE,
    MILEAGE_TOLERANCE_MILES,
    COLOR_MISMATCH_MAJORITY,
)
from core.logger import calculate_cost
from core.verifier import verify_listing, Flag, normalize_drivetrain
from corpus.storage import get_auction_detail
from eval.inject_real_errors import build_baseline, DEFAULT_OUT as GROUND_TRUTH_PATH

# Hardcoded per-agent model strings, matching what each agents/*.py module
# actually calls -- recorded here (not introspected) since that's the same
# way the rest of this codebase already tracks model identity.
MODEL_VERSIONS = {
    "extraction": "claude-sonnet-4-6",
    "photo": "claude-sonnet-4-6",
    "synthesis": "claude-sonnet-4-6",
}

EVAL_DIR = Path(__file__).parent
ROUND1_STATE_PATH = EVAL_DIR / "round1_state.json"
ROUND1_RESULTS_PATH = EVAL_DIR / "round1_results.json"
ROUND2_STATE_PATH = EVAL_DIR / "round2_state.json"
ROUND2_LOCAL_REPORTS_PATH = EVAL_DIR / "round2_local_reports.json"
RESULTS_PATH = EVAL_DIR / "results.json"

SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2}

_STUB_EDITORIAL = EditorialFlags(
    highlights_text="",
    has_consistent_voice=True,
    missing_sections=[],
    grammar_issues=[],
    completeness_score=1.0,
    notes="Editorial agent skipped for eval -- no ground truth available for highlights quality.",
)

# Same heuristic aliasing the old CSV harness used -- a ground-truth
# error_field doesn't always exactly match the Flag.field_name string
# core/verifier.py produces.
ERROR_FIELD_ALIASES: dict[str, list[str]] = {
    "engine_displacement": ["engine_displacement"],
    "engine_cylinders": ["engine_cylinders"],
    "mileage": ["mileage"],
    "make": ["make"],
    "year": ["year"],
    "color": ["color"],
    "transmission": ["transmission"],
    "drivetrain": ["drivetrain"],
    "duplicate_photos": ["duplicate_photos"],
    "photo_angles": ["photo_angles"],
}


# photo_angles is included here for a structural reason, not a data-quality
# one: real listings only get ~8-11 sampled photos (a deliberate cost
# trade-off, see corpus/scrape_listing_details.py's PHOTO_SAMPLE_COUNTS)
# against 16 required fine-grained angles, so check_photo_angles is close to
# guaranteed to fire several INFO-level flags on every listing regardless of
# what error was injected. Excluding it here only affects the false-positive
# side of scoring -- _matches_expected_field already routes a photo_angles
# flag into the true-positive/catch path on a missing_angle row (the one
# error type that actually targets this field) before this set is ever
# checked, so this doesn't hide it from being tested where it matters.
SYNTHETIC_NOISE_FIELDS = {"photo_verification", "vin_verification", "editorial_completeness", "photo_angles", "vin_pre_standard_era"}


# Cars & Bids house style opens the Highlights section with "THIS... is a
# YYYY ..." -- but "..." is rendered as either three literal ASCII periods
# or a single U+2026 ellipsis character depending on the listing. Measured:
# 96/497 (19%) of the real corpus uses the Unicode form, which a literal
# "\.\.\." pattern silently never matches -- defeating the year/make patches
# below for a fifth of listings without any visible error.
_ELLIPSIS_RE = r"(?:\.\.\.|…)"


def _patch_seller_description_year(description: str, real_year, claimed_year) -> str:
    """The Cars & Bids house style always opens the Highlights section with
    'THIS... is a YYYY ...' -- the listing's own explicit year claim. Patching
    only this occurrence (not every 4-digit number in the prose, which would
    also corrupt unrelated years like a model-history production date or a
    service-record date) keeps the injected error consistent with the one
    place the listing actually asserts its own model year."""
    pattern = re.compile(r"(THIS" + _ELLIPSIS_RE + r"\s+is\s+a\s+)" + re.escape(str(real_year)))
    patched, n = pattern.subn(rf"\g<1>{claimed_year}", description, count=1)
    return patched if n else description


def _patch_seller_description_make(description: str, real_make: Optional[str], claimed_make: str) -> str:
    """Patches the opening 'THIS... is a YYYY MAKE ...' line, then sweeps
    the rest of the prose for any other whole-word/whole-phrase mention of
    the real make and replaces it too. The sweep exists because the Cars &
    Bids house-style model-history paragraph independently repeats the real
    make later in the body -- measured: of listings where only the opening
    line was patched, 86% still had the real make restated in unpatched
    prose, and extraction followed that residual evidence over the patched
    opening line and its own "don't infer the make" instruction. This was
    the dominant cause of make_error's real-world recall collapse.

    Known residual limitation, not fixed here: a shortened form used
    elsewhere in prose (e.g. real make "Mercedes-Benz" referred to later as
    just "Mercedes") won't be caught by this phrase-exact regex.

    real_make can in principle be None even though inject_make_error itself
    already guards against it (see eval/inject_real_errors.py) -- guarded
    here too for defense in depth, same reasoning as the color patch's
    None-guard added alongside this one."""
    if not real_make:
        return description
    opening = re.compile(r"(THIS" + _ELLIPSIS_RE + r"\s+is\s+a\s+\d{4}\s+)" + re.escape(real_make), re.IGNORECASE)
    description, _ = opening.subn(rf"\g<1>{claimed_make}", description, count=1)

    # Land Rover's sub-brand name "Range Rover" is often used in place of
    # the manufacturer name in prose -- sweep it into the same replacement
    # whenever the real make is Land Rover.
    names_to_replace = [real_make]
    if real_make.strip().lower() == "land rover":
        names_to_replace.append("Range Rover")
    for name in names_to_replace:
        pattern = re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
        description = pattern.sub(claimed_make, description)
    return description


def _patch_seller_description_color(description: str, real_color: Optional[str], claimed_color: str) -> str:
    """The opening line also always states exterior color right after
    'finished in' (agents/editorial_agent.py's house-style template) --
    case can differ from the structured field (e.g. structured 'White' vs
    prose 'white'), so this matches case-insensitively. Same one-occurrence
    reasoning as the year/make patches above.

    real_color can be None -- a real scraper gap confirmed at 500-listing
    scale (3 real auctions have no exterior_color captured). re.escape()
    crashes on None with no str() coercion, and this crash previously took
    down the entire batch submission with no exception handling around it
    -- see submit_round1's try/except, added alongside this fix."""
    if not real_color:
        return description
    pattern = re.compile(r"(finished in )" + re.escape(real_color), re.IGNORECASE)
    patched, n = pattern.subn(rf"\g<1>{claimed_color}", description, count=1)
    return patched if n else description


_TRANSMISSION_TYPE_WORDS = ["manual", "automatic", "cvt"]


def _transmission_type_word(value: Optional[str]) -> Optional[str]:
    value = (value or "").lower()
    for word in _TRANSMISSION_TYPE_WORDS:
        if word in value:
            return word
    return None


def _patch_seller_description_transmission(description: str, real_transmission: str, claimed_transmission: str) -> str:
    """The house style restates transmission type at least once (the
    powertrain bullet's '...via a [transmission] transmission') and often a
    second time earlier in the write-up too, with different surrounding
    wording each time -- rather than anchor to one exact sentence shape,
    this swaps every case-insensitive whole-word mention of the real type
    word (manual/automatic/cvt) for the claimed one, since that's the exact
    signal core/verifier.py's normalize_transmission() itself keys off."""
    real_word = _transmission_type_word(real_transmission)
    claimed_word = _transmission_type_word(claimed_transmission)
    if not real_word or not claimed_word:
        return description
    pattern = re.compile(r"\b" + re.escape(real_word) + r"\b", re.IGNORECASE)
    return pattern.sub(claimed_word, description)


# Natural-language phrasing the house style uses for each drivetrain in the
# powertrain bullet ("Output is sent to <phrase> via a ... transmission").
# AWD and 4WD share a phrase since both genuinely read as "all four wheels"
# in plain English -- there's no prose difference to fix between them.
_DRIVE_PHRASE = {
    "RWD": "the rear wheels",
    "FWD": "the front wheels",
    "AWD": "all four wheels",
    "4WD": "all four wheels",
}


def _patch_seller_description_engine(description: str, real_engine: str, claimed_engine: str, error_field: str) -> str:
    """The powertrain bullet always states the engine right after 'Power
    comes from a' (e.g. 'Power comes from a 2.0-liter turbocharged
    inline-4, rated at 211 horsepower...' -- see
    agents/editorial_agent.py's house style). Found via the M7 checkpoint:
    engine_error's catchability depended entirely on which real listing the
    round-robin happened to assign it to, because this bullet was never
    patched -- same class of leak as year/make/color/transmission/
    drivetrain/mileage, just not exercised until a reshuffle changed which
    listings got this error type.

    Scoped tightly to the phrase right after "Power comes from a", not a
    global sweep -- horsepower/torque/mileage figures sit in the very same
    sentence and must not get touched."""
    if error_field == "engine_displacement":
        real_match = re.search(r"(\d+\.\d+)\s*L", real_engine or "")
        claimed_match = re.search(r"(\d+\.\d+)\s*L", claimed_engine or "")
        if not real_match or not claimed_match:
            return description
        pattern = re.compile(r"(Power comes from a )" + re.escape(real_match.group(1)) + r"(-liter)", re.IGNORECASE)
        patched, n = pattern.subn(rf"\g<1>{claimed_match.group(1)}\g<2>", description, count=1)
        return patched if n else description
    if error_field == "engine_cylinders":
        from core.verifier import normalize_cylinders
        real_cyl = normalize_cylinders(real_engine)
        claimed_cyl = normalize_cylinders(claimed_engine)
        if real_cyl is None or claimed_cyl is None:
            return description
        # The cylinder count is the last token of the engine-config word
        # (inline-4, V6, flat-6) that follows the displacement -- capturing
        # everything up to the next comma keeps this from matching a
        # horsepower/torque number later in the same sentence.
        pattern = re.compile(r"(Power comes from a [\d.]+-liter[^,.]*?)\b" + str(real_cyl) + r"\b")
        patched, n = pattern.subn(rf"\g<1>{claimed_cyl}", description, count=1)
        return patched if n else description
    return description


# Beyond the powertrain bullet's "wheels" phrase (which can't be swept
# globally -- see _patch_seller_description_drivetrain's docstring), real
# listings sometimes restate the drivetrain elsewhere as a bare acronym or
# spelled-out phrase (a spec bullet, "all-wheel drive standard on every
# trim"). These specific tokens don't carry the same collision risk as the
# generic word "wheels", so they're safe to sweep like make_error's sweep.
_DRIVETRAIN_TOKEN_PATTERNS = {
    "RWD": [r"\bRWD\b", r"\brear[\s-]wheel drive\b"],
    "FWD": [r"\bFWD\b", r"\bfront[\s-]wheel drive\b"],
    "AWD": [r"\bAWD\b", r"\ball[\s-]wheel drive\b"],
    "4WD": [r"\b4WD\b", r"\bfour[\s-]wheel drive\b", r"\b4x4\b"],
}


def _patch_seller_description_drivetrain(description: str, real_drivetrain: str, claimed_drivetrain: str) -> str:
    """Two passes: (1) the powertrain bullet's 'Output is sent to <wheels>
    via' phrase, scoped tightly to that one sentence -- NOT swept globally,
    since 'front/rear wheels' also shows up in unrelated contexts in real
    listings (curb rash, wheel service records) that must not get rewritten
    just because they share the same words; (2) a sweep of the real
    drivetrain's bare acronym/spelled-out forms (_DRIVETRAIN_TOKEN_PATTERNS
    above) anywhere else in the prose. Closing this second gap mirrors what
    actually fixed make_error's self-correction problem
    (_patch_seller_description_make above): a listing restating the real
    drivetrain later in a spec bullet or trim description was enough for
    extraction to override the injected lie in the labeled Drivetrain
    field, even with the powertrain-bullet phrase itself correctly patched
    (confirmed on 2 real eval misses, auction_ids KVMlLMLx/K17ao0Dx)."""
    real_key = normalize_drivetrain(real_drivetrain)
    claimed_key = normalize_drivetrain(claimed_drivetrain)

    real_phrase = _DRIVE_PHRASE.get(real_key)
    claimed_phrase = _DRIVE_PHRASE.get(claimed_key)
    if real_phrase and claimed_phrase and real_phrase != claimed_phrase:
        pattern = re.compile(r"(Output is sent to )" + re.escape(real_phrase) + r"( via)", re.IGNORECASE)
        description = pattern.sub(rf"\g<1>{claimed_phrase}\g<2>", description)

    if real_key in _DRIVETRAIN_TOKEN_PATTERNS and real_key != claimed_key and claimed_key:
        for pattern_str in _DRIVETRAIN_TOKEN_PATTERNS[real_key]:
            description = re.compile(pattern_str, re.IGNORECASE).sub(claimed_key, description)

    return description


# --- Reproduce the tampered listing from the ground-truth manifest (no re-run of the injector) ---
def apply_mutation(baseline: dict, entry: dict) -> tuple[dict, Optional[bool]]:
    """Mutates a copy of build_baseline()'s output using only the fields the
    ground-truth manifest recorded -- claimed_value for structured-field
    injectors, mutation_detail for the two photo-list injectors.

    Returns (mutated, prose_patch_applied). prose_patch_applied is True/False
    for the 6 fields with a prose-patch function (whether the regex actually
    matched and rewrote the text), or None for the two photo-based injectors
    and for "mileage" (deliberately never patched -- see inject_mileage_drift's
    docstring), none of which have a patch to apply. This distinguishes "the
    pipeline missed a well-planted lie" from "the lie was never really
    planted because this listing's phrasing didn't match the patch regex" --
    previously indistinguishable after the fact."""
    mutated = dict(baseline)
    mutated["photos"] = list(baseline["photos"])
    field = entry["error_field"]
    claimed = entry.get("claimed_value")
    prose_patch_applied = None

    def _patched(patch_fn, *args):
        before = mutated["seller_description"]
        after = patch_fn(*args)
        mutated["seller_description"] = after
        return after != before

    if field == "year":
        mutated["year"] = int(claimed)
        prose_patch_applied = _patched(
            _patch_seller_description_year, mutated["seller_description"], baseline["year"], claimed)
    elif field == "make":
        mutated["make"] = claimed
        prose_patch_applied = _patched(
            _patch_seller_description_make, mutated["seller_description"], baseline["make"], claimed)
    elif field == "mileage":
        mutated["mileage"] = claimed
        # No prose patch -- inject_mileage_drift (eval/inject_real_errors.py)
        # deliberately leaves seller_description untouched. The real,
        # unpatched Carfax checkpoint contradicting this mutated claimed
        # value IS the signal check_mileage_consistency looks for; patching
        # it out would defeat the check being tested. prose_patch_applied
        # stays None here (same as the two photo-based injectors) since
        # there's no patch to have applied.
    elif field == "transmission":
        mutated["transmission"] = claimed
        prose_patch_applied = _patched(
            _patch_seller_description_transmission, mutated["seller_description"], baseline["transmission"], claimed)
    elif field == "drivetrain":
        mutated["drivetrain"] = claimed
        prose_patch_applied = _patched(
            _patch_seller_description_drivetrain, mutated["seller_description"], baseline["drivetrain"], claimed)
    elif field in ("engine_displacement", "engine_cylinders"):
        mutated["engine"] = claimed
        prose_patch_applied = _patched(
            _patch_seller_description_engine, mutated["seller_description"], baseline["engine"], claimed, field)
    elif field == "color":
        mutated["exterior_color"] = claimed
        prose_patch_applied = _patched(
            _patch_seller_description_color, mutated["seller_description"], baseline["exterior_color"], claimed)
    elif field == "duplicate_photos":
        detail = entry["mutation_detail"]
        mutated["photos"].append({"category": detail["category"], "url": detail["url"]})
    elif field == "photo_angles":
        detail = entry["mutation_detail"]
        mutated["photos"] = [p for p in mutated["photos"] if p["category"] != detail["category"]]
    else:
        raise ValueError(f"Unknown error_field in ground truth: {field}")

    return mutated, prose_patch_applied


def build_raw_listing_text(baseline: dict) -> str:
    lines = [
        f"Make\n{baseline['make']}",
        f"Model\n{baseline['model']}",
        f"Year\n{baseline['year']}",
        f"Trim\n{baseline.get('trim') or ''}",
        f"VIN\n{baseline['vin']}",
        f"Mileage\n{baseline['mileage']}",
        f"Exterior Color\n{baseline['exterior_color']}",
        f"Interior Color\n{baseline.get('interior_color') or ''}",
        f"Engine\n{baseline['engine']}",
        f"Transmission\n{baseline['transmission']}",
        f"Drivetrain\n{baseline['drivetrain']}",
        f"Highlights\n{baseline['seller_description']}",
    ]
    return "\n".join(lines)


def _matches_expected_field(flag: Flag, error_field: str) -> bool:
    aliases = ERROR_FIELD_ALIASES.get(error_field, [error_field])
    return flag.field_name in aliases


# --- Round 1: submit ---
def submit_round1(limit: int | None = None):
    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)
    if limit:
        ground_truth = ground_truth[:limit]

    if not ground_truth:
        print(f"No ground-truth entries found at {GROUND_TRUTH_PATH}. Run eval/inject_real_errors.py first.")
        return

    requests = []
    custom_id_map = {}
    entries_state = {}

    for entry in ground_truth:
        auction_id = entry["auction_id"]
        detail = get_auction_detail(auction_id)
        if detail is None:
            print(f"  {auction_id}: no auction_details row in corpus.db, skipping")
            continue

        # Wrapped end-to-end: a single listing hitting an unexpected data
        # gap (e.g. a real, confirmed case at 500-listing scale -- a
        # missing exterior_color crashing apply_mutation's color-prose
        # patch with no guard) must never take down the whole submission.
        # Before this fix, one bad listing crashed the entire batch
        # mid-run, discarding all photo-fetch work already done for every
        # other listing processed before it -- same fragility class already
        # fixed once in inject_real_errors.py's build_ground_truth loop,
        # but never applied here until this was hit for real.
        try:
            baseline = build_baseline(detail)
            mutated, prose_patch_applied = apply_mutation(baseline, entry)

            raw_text = build_raw_listing_text(mutated)
            extract_custom_id = f"{auction_id}__extract"
            extract_request = extraction_agent.build_batch_request(extract_custom_id, raw_text)

            photo_requests = []
            photo_custom_id_infos = []
            photo_custom_ids = []
            failed_photo_urls = []
            for i, photo in enumerate(mutated["photos"]):
                photo_custom_id = f"{auction_id}__photo{i}"
                try:
                    request, phash = photo_agent.build_batch_request(photo_custom_id, photo["url"])
                except Exception as e:
                    print(f"    {auction_id}: failed to fetch photo {photo['url']}: {e}")
                    failed_photo_urls.append(photo["url"])
                    continue
                photo_requests.append(request)
                photo_custom_id_infos.append((photo_custom_id, {
                    "auction_id": auction_id, "kind": "photo",
                    "url": photo["url"], "phash": phash, "category": photo["category"],
                }))
                photo_custom_ids.append(photo_custom_id)

            vin_data = verify_vin(mutated["vin"])
        except Exception as e:
            print(f"  {auction_id}: unexpected error building this listing's requests ({e}), skipping this auction")
            continue

        requests.append(extract_request)
        custom_id_map[extract_custom_id] = {"auction_id": auction_id, "kind": "extract"}
        requests.extend(photo_requests)
        for cid, info in photo_custom_id_infos:
            custom_id_map[cid] = info

        entries_state[auction_id] = {
            **entry,
            "vin_data": vin_data.model_dump(),
            "prose_patch_applied": prose_patch_applied,
            "location": mutated.get("location"),
            "seller_type": mutated.get("seller_type"),
            "title_status": mutated.get("title_status"),
            "body_style": mutated.get("body_style"),
            "url": mutated.get("url"),
            "extract_custom_id": extract_custom_id,
            "photo_custom_ids": photo_custom_ids,
            "failed_photo_urls": failed_photo_urls,
        }

    if not requests:
        print("Nothing to submit.")
        return

    # Split into several smaller batches rather than one giant submission,
    # chunked by actual serialized BYTE SIZE, not request count. Found the
    # hard way, twice: an unchunked ~6,353-request batch died with no
    # diagnosable cause (confirmed via Anthropic's own batch list that
    # nothing was created server-side -- no cost lost, but no error either,
    # since there was no error handling around the call at all). A first
    # attempt at chunking split evenly by request COUNT into 3 pieces, but
    # photo payload size varies a lot per listing, so an even 3-way split
    # doesn't guarantee any given chunk stays under the API's actual hard
    # limit -- confirmed directly: chunk 1/3 (2,116 requests) was rejected
    # with a real, now-caught error: "Error code: 413 ... Request exceeds
    # the maximum size. The Message Batches API accepts requests up to
    # 256MBs." Chunking by measured size avoids this regardless of how
    # unevenly photo sizes are distributed across listings. custom_id_map
    # is global and flat (custom_ids are already unique across the whole
    # run), so which physical batch a request lands in doesn't matter for
    # fetch_round1 -- chunk boundaries don't need to align with listing
    # boundaries.
    MAX_CHUNK_BYTES = 150 * 1024 * 1024  # 150MB -- well under the 256MB hard
    # limit, leaving margin for JSON-serialization-size vs. real-wire-size
    # estimation error.

    def _request_size_bytes(request) -> int:
        return len(json.dumps(request).encode("utf-8"))

    chunks = []
    current_chunk = []
    current_size = 0
    for req in requests:
        req_size = _request_size_bytes(req)
        if current_chunk and current_size + req_size > MAX_CHUNK_BYTES:
            chunks.append(current_chunk)
            current_chunk = []
            current_size = 0
        current_chunk.append(req)
        current_size += req_size
    if current_chunk:
        chunks.append(current_chunk)

    batch_ids = []
    for i, chunk in enumerate(chunks, 1):
        chunk_mb = sum(_request_size_bytes(r) for r in chunk) / (1024 * 1024)
        print(f"Submitting batch {i}/{len(chunks)}: {len(chunk)} requests, ~{chunk_mb:.1f}MB ...")
        try:
            # Explicit timeout so a genuine network stall fails loudly
            # (raises) instead of hanging indefinitely with no visible
            # progress -- also observed directly today: a chunk that turned
            # out to be oversized appeared "hung" (identical CPU/memory
            # across repeated checks) for several minutes before finally
            # surfacing the real 413 error: the upload itself was slow for
            # a large payload, and there was no timeout to force an earlier,
            # clearer failure.
            batch = extraction_agent.raw_client.messages.batches.create(requests=chunk, timeout=300.0)
        except Exception as e:
            print(f"  FAILED to create batch {i}/{len(chunks)}: {type(e).__name__}: {e}")
            print(f"  {len(batch_ids)} batch(es) were successfully created before this failure -- "
                  "saving state for those now rather than losing that progress.")
            break
        print(f"  Batch {i}/{len(chunks)} created: {batch.id} (status: {batch.processing_status})")
        batch_ids.append(batch.id)

    if not batch_ids:
        print("No batches were successfully created. Nothing saved.")
        return

    print(f"\n{len(entries_state)} listings ({len(requests)} requests) submitted across {len(batch_ids)} batch(es).")

    state = {
        "batch_ids": batch_ids,
        "custom_id_map": custom_id_map,
        "entries": entries_state,
    }
    with open(ROUND1_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Saved round-1 state to {ROUND1_STATE_PATH}. Run fetch-round1 later.")


# --- Round 1: fetch ---
def fetch_round1():
    if not ROUND1_STATE_PATH.exists():
        print(f"No pending round-1 batch found at {ROUND1_STATE_PATH}. Run submit first.")
        return

    with open(ROUND1_STATE_PATH) as f:
        state = json.load(f)

    batch_ids = state["batch_ids"]
    batches = [extraction_agent.raw_client.messages.batches.retrieve(bid) for bid in batch_ids]
    for batch in batches:
        print(f"Batch {batch.id}: {batch.processing_status} "
              f"(succeeded={batch.request_counts.succeeded}, "
              f"errored={batch.request_counts.errored}, "
              f"processing={batch.request_counts.processing})")

    if any(b.processing_status != "ended" for b in batches):
        print("Not all batches are finished yet -- check back later.")
        return

    custom_id_map = state["custom_id_map"]
    entries = state["entries"]

    listing_data_by_auction = {}
    photos_by_auction = defaultdict(list)  # auction_id -> [(PhotoAnalysis, category)]
    hashes_by_auction = defaultdict(list)
    errors_by_auction = defaultdict(list)
    usage_by_auction = defaultdict(lambda: {
        "extraction_input_tokens": 0, "extraction_output_tokens": 0,
        "photo_input_tokens": 0, "photo_output_tokens": 0,
    })

    def _process_result(result):
        info = custom_id_map.get(result.custom_id)
        if info is None:
            print(f"  WARNING: unrecognized custom_id {result.custom_id}, skipping")
            return
        auction_id = info["auction_id"]

        if result.result.type != "succeeded":
            print(f"  {result.custom_id}: {result.result.type}, skipping")
            errors_by_auction[auction_id].append(result.custom_id)
            return

        message = result.result.message
        # Usage is captured regardless of whether content parsing below
        # succeeds -- it's a property of the API response itself, not of
        # whether we could make sense of the content, so a malformed-but-
        # billed response should still count toward real cost.
        usage = getattr(message, "usage", None)
        if usage is not None:
            prefix = "extraction" if info["kind"] == "extract" else "photo"
            usage_by_auction[auction_id][f"{prefix}_input_tokens"] += usage.input_tokens
            usage_by_auction[auction_id][f"{prefix}_output_tokens"] += usage.output_tokens

        try:
            if info["kind"] == "extract":
                listing_data_by_auction[auction_id] = extraction_agent.parse_batch_result(message)
            else:
                photo = photo_agent.parse_batch_result(info["url"], message)
                photos_by_auction[auction_id].append((photo, info.get("category")))
                hashes_by_auction[auction_id].append((info["url"], info.get("phash")))
        except Exception as e:
            # A single malformed response (e.g. the model returning a field
            # in an unexpected shape) must not take down every other
            # already-succeeded result in a 100+ request batch -- record it
            # against this one auction and keep going, same spirit as the
            # "result.type != succeeded" branch above.
            print(f"  {result.custom_id}: failed to parse ({e}), skipping")
            errors_by_auction[auction_id].append(result.custom_id)

    # custom_id_map is global/flat across all batches (custom_ids are
    # already unique across the whole run), so results from every batch
    # just get merged into the same per-auction accumulators regardless of
    # which physical batch they came from.
    for bid in batch_ids:
        for result in extraction_agent.raw_client.messages.batches.results(bid):
            _process_result(result)

    round1_results = {}
    for auction_id, entry in entries.items():
        listing_data = listing_data_by_auction.get(auction_id)
        if listing_data is None:
            print(f"  {auction_id}: extraction result missing, skipping this listing entirely")
            continue

        photo_pairs = photos_by_auction.get(auction_id, [])
        photo_data = [p for p, _cat in photo_pairs]
        vin_data = VINData(**entry["vin_data"])
        duplicate_pairs = detect_duplicate_photos(hashes_by_auction.get(auction_id, []))

        # Eval-corpus-specific fix: most of corpus.db's already-scraped photo
        # lists have the same photo indexed twice under two different
        # categories (a scraper dedup gap fixed going forward in
        # corpus/scrape_listing_details.py, but not retroactive for data
        # already scraped) -- detect_duplicate_photos correctly reports these
        # as perceptual matches, since they genuinely are the same image, but
        # they aren't a real "listing reused a photo" signal. The
        # inject_duplicate_photo injector uses this exact same mechanism
        # (reusing an existing photo's byte-identical URL) to plant its
        # signal, so a pair can't be judged real vs. artifact from the URLs
        # alone -- ground truth is used here to tell them apart: for a
        # duplicate_photo-type row, keep only the pair matching the actual
        # injected URL (claimed_value); for every other row, any pair found
        # is the scraper artifact, not a real defect, and is dropped. This
        # has no equivalent in app.py's live path -- production has no
        # ground truth to lean on, so it relies solely on the scraper fix.
        if entry["error_type"] == "duplicate_photo":
            claimed = entry.get("claimed_value")
            duplicate_pairs = [p for p in duplicate_pairs if claimed in (p[0], p[1])]
        else:
            duplicate_pairs = []

        flags, summary = verify_listing(listing_data, vin_data, photo_data, _STUB_EDITORIAL, duplicate_pairs)

        usage = usage_by_auction.get(auction_id, {
            "extraction_input_tokens": 0, "extraction_output_tokens": 0,
            "photo_input_tokens": 0, "photo_output_tokens": 0,
        })
        extraction_cost = calculate_cost(
            usage["extraction_input_tokens"], usage["extraction_output_tokens"], MODEL_VERSIONS["extraction"])
        photo_cost = calculate_cost(
            usage["photo_input_tokens"], usage["photo_output_tokens"], MODEL_VERSIONS["photo"])

        round1_results[auction_id] = {
            **{k: entry[k] for k in (
                "error_type", "error_field", "claimed_value", "correct_value",
                "expected_flag_severity", "expected_overall_verdict",
                "original_error_type", "reassigned", "reassignment_reason",
                "prose_patch_applied", "location", "seller_type", "title_status",
                "body_style", "url",
            )},
            "vin_data": entry["vin_data"],
            "listing_data": listing_data.model_dump(),
            "flags": [f.model_dump() for f in flags],
            "verification_summary": summary.model_dump(),
            "photos": [
                {**p.model_dump(), "category": cat} for p, cat in photo_pairs
            ],
            "duplicate_photo_pairs": [
                {"url_a": a, "url_b": b, "hamming_distance": d} for a, b, d in duplicate_pairs
            ],
            "usage": usage,
            "cost_usd": {
                "extraction": round(extraction_cost, 6),
                "photo": round(photo_cost, 6),
                "total": round(extraction_cost + photo_cost, 6),
            },
            "batch_errors": errors_by_auction.get(auction_id, []),
        }

    with open(ROUND1_RESULTS_PATH, "w") as f:
        json.dump(round1_results, f, indent=2)
    print(f"\n{len(round1_results)} listings processed through extraction + photo vision + verifier.")
    print(f"Round-1 results written to {ROUND1_RESULTS_PATH}.")


# --- Round 2: submit ---
def submit_round2():
    if not ROUND1_RESULTS_PATH.exists():
        print(f"No round-1 results found at {ROUND1_RESULTS_PATH}. Run fetch-round1 first.")
        return

    with open(ROUND1_RESULTS_PATH) as f:
        round1_results = json.load(f)

    requests = []
    custom_id_map = {}
    local_reports = {}

    for auction_id, r in round1_results.items():
        flags = [Flag(**f) for f in r["flags"]]

        if not flags:
            action = compute_action(flags)
            score = compute_score(flags, action)
            local_reports[auction_id] = {
                "overall_score": score,
                "flags": [],
                "summary_paragraph": NO_ISSUES_SUMMARY,
                "recommended_action": action,
                "synthesis_usage": {"input_tokens": 0, "output_tokens": 0},
                "synthesis_cost_usd": 0.0,
            }
            continue

        custom_id = f"{auction_id}__synth"
        request = synthesis_agent.build_batch_request(custom_id, flags)
        requests.append(request)
        custom_id_map[custom_id] = auction_id

    with open(ROUND2_LOCAL_REPORTS_PATH, "w") as f:
        json.dump(local_reports, f, indent=2)
    print(f"{len(local_reports)} listings had no flags -- reports built locally, no LLM call needed.")

    if not requests:
        print("No listings needed a synthesis call.")
        return

    print(f"Submitting a batch of {len(requests)} synthesis requests ...")
    batch = extraction_agent.raw_client.messages.batches.create(requests=requests)
    print(f"Batch created: {batch.id} (status: {batch.processing_status})")

    state = {"batch_id": batch.id, "custom_id_map": custom_id_map}
    with open(ROUND2_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Saved round-2 state to {ROUND2_STATE_PATH}. Run fetch-round2 later.")


# --- Round 2: fetch + final comparison ---
def fetch_round2():
    if not ROUND1_RESULTS_PATH.exists():
        print(f"No round-1 results found at {ROUND1_RESULTS_PATH}. Run fetch-round1 first.")
        return

    with open(ROUND1_RESULTS_PATH) as f:
        round1_results = json.load(f)

    with open(ROUND2_LOCAL_REPORTS_PATH) as f:
        reports = json.load(f)

    round2_batch_created_at = None
    round2_batch_ended_at = None
    round2_batch_id = None

    if ROUND2_STATE_PATH.exists():
        with open(ROUND2_STATE_PATH) as f:
            state = json.load(f)

        batch = extraction_agent.raw_client.messages.batches.retrieve(state["batch_id"])
        print(f"Batch {batch.id}: {batch.processing_status} "
              f"(succeeded={batch.request_counts.succeeded}, "
              f"errored={batch.request_counts.errored}, "
              f"processing={batch.request_counts.processing})")

        if batch.processing_status != "ended":
            print("Batch not finished yet -- check back later.")
            return

        round2_batch_id = batch.id
        round2_batch_created_at = str(getattr(batch, "created_at", None))
        round2_batch_ended_at = str(getattr(batch, "ended_at", None))

        custom_id_map = state["custom_id_map"]
        for result in extraction_agent.raw_client.messages.batches.results(state["batch_id"]):
            auction_id = custom_id_map.get(result.custom_id)
            if auction_id is None:
                print(f"  WARNING: unrecognized custom_id {result.custom_id}, skipping")
                continue
            if result.result.type != "succeeded":
                print(f"  {result.custom_id}: {result.result.type}, skipping")
                continue

            message = result.result.message
            usage = getattr(message, "usage", None)
            synthesis_usage = {
                "input_tokens": usage.input_tokens if usage else 0,
                "output_tokens": usage.output_tokens if usage else 0,
            }
            synthesis_cost = calculate_cost(
                synthesis_usage["input_tokens"], synthesis_usage["output_tokens"], MODEL_VERSIONS["synthesis"])

            summary = synthesis_agent.parse_batch_result(message)
            flags = [Flag(**f) for f in round1_results[auction_id]["flags"]]
            action = compute_action(flags)
            score = compute_score(flags, action)
            reports[auction_id] = {
                "overall_score": score,
                "flags": round1_results[auction_id]["flags"],
                "summary_paragraph": summary,
                "recommended_action": action,
                "synthesis_usage": synthesis_usage,
                "synthesis_cost_usd": round(synthesis_cost, 6),
            }
    else:
        print("No round-2 batch was submitted (every listing had no flags) -- using local reports only.")

    # Round-1 batch metadata, for the run-metadata block below -- re-retrieved
    # (free, idempotent) rather than persisted earlier, so fetch_round1 stays
    # focused purely on its own round and doesn't need to know about
    # run-metadata assembly, which only makes sense once the whole run (both
    # rounds) is complete.
    # Round 1 may now span several batches (see submit_round1's chunking) --
    # record all of them, not just one.
    round1_batches_meta = []
    if ROUND1_STATE_PATH.exists():
        with open(ROUND1_STATE_PATH) as f:
            round1_state = json.load(f)
        for bid in round1_state["batch_ids"]:
            b = extraction_agent.raw_client.messages.batches.retrieve(bid)
            round1_batches_meta.append({
                "batch_id": bid,
                "created_at": str(getattr(b, "created_at", None)),
                "ended_at": str(getattr(b, "ended_at", None)),
            })

    # --- Compare every listing against its ground-truth entry ---
    per_error_type = defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0})
    verdict_confusion = defaultdict(lambda: defaultdict(int))
    per_row_results = []

    for auction_id, r in round1_results.items():
        report = reports.get(auction_id)
        if report is None:
            print(f"  {auction_id}: no synthesis report (round-2 result missing), skipping comparison")
            continue

        flags = [Flag(**f) for f in r["flags"]]
        error_field = r["error_field"]
        expected_severity = r["expected_flag_severity"]
        error_type = r["error_type"]

        matching_flags = [f for f in flags if _matches_expected_field(f, error_field)]
        caught = any(
            SEVERITY_ORDER.get(f.severity, 99) <= SEVERITY_ORDER.get(expected_severity, 99)
            for f in matching_flags
        )

        if caught:
            per_error_type[error_type]["tp"] += 1
        else:
            per_error_type[error_type]["fn"] += 1

        false_positive_flags = [
            f for f in flags
            if not _matches_expected_field(f, error_field) and f.field_name not in SYNTHETIC_NOISE_FIELDS
        ]
        per_error_type[error_type]["fp"] += len(false_positive_flags)

        expected_verdict = r["expected_overall_verdict"]
        verdict_confusion[expected_verdict][report["recommended_action"]] += 1

        round1_cost = r.get("cost_usd", {}).get("total", 0.0)
        synthesis_cost = report.get("synthesis_cost_usd", 0.0)

        per_row_results.append({
            "auction_id": auction_id,
            "error_type": error_type,
            "error_field": error_field,
            "expected_flag_severity": expected_severity,
            "caught": caught,
            # Full Flag objects, not just field_name lists -- this is what
            # makes confidence calibration and threshold-sensitivity
            # analysis possible later; a bare name list drops confidence/
            # severity/claimed/verified values.
            "matching_flags": [f.model_dump() for f in matching_flags],
            "false_positive_flags": [f.model_dump() for f in false_positive_flags],
            "expected_overall_verdict": expected_verdict,
            "actual_overall_verdict": report["recommended_action"],
            "verdict_match": expected_verdict == report["recommended_action"],
            "overall_score": report["overall_score"],
            "summary_paragraph": report["summary_paragraph"],
            "cost_usd": {
                "extraction_and_photo": round(round1_cost, 6),
                "synthesis": round(synthesis_cost, 6),
                "total": round(round1_cost + synthesis_cost, 6),
            },
            # Original-error-type/reassignment trail and geographic/seller
            # fields, carried through from round1_results so a dashboard can
            # read everything about a listing from this one row.
            "original_error_type": r.get("original_error_type"),
            "reassigned": r.get("reassigned"),
            "reassignment_reason": r.get("reassignment_reason"),
            "prose_patch_applied": r.get("prose_patch_applied"),
            "location": r.get("location"),
            "seller_type": r.get("seller_type"),
            "title_status": r.get("title_status"),
            "body_style": r.get("body_style"),
            "url": r.get("url"),
        })

    per_error_type_metrics = {}
    for error_type, counts in per_error_type.items():
        tp, fn, fp = counts["tp"], counts["fn"], counts["fp"]
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        f1 = (2 * precision * recall / (precision + recall)) if precision and recall and (precision + recall) else None
        per_error_type_metrics[error_type] = {
            "tp": tp, "fn": fn, "fp": fp,
            "precision": round(precision, 3) if precision is not None else None,
            "recall": round(recall, 3) if recall is not None else None,
            "f1": round(f1, 3) if f1 is not None else None,
        }

    total_verdict_matches = sum(1 for r in per_row_results if r["verdict_match"])

    results = {
        "per_field_metrics": per_error_type_metrics,
        "verdict_confusion_matrix": {k: dict(v) for k, v in verdict_confusion.items()},
        "verdict_accuracy": round(total_verdict_matches / len(per_row_results), 3) if per_row_results else None,
        "run_metadata": {
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "round1_batches": round1_batches_meta,
            "round2_batch_id": round2_batch_id,
            "round2_batch_created_at": round2_batch_created_at,
            "round2_batch_ended_at": round2_batch_ended_at,
            "model_versions": MODEL_VERSIONS,
            "thresholds": {
                "CONFIDENCE_FLOOR": CONFIDENCE_FLOOR,
                "ENGINE_DISPLACEMENT_TOLERANCE": ENGINE_DISPLACEMENT_TOLERANCE,
                "MILEAGE_TOLERANCE_MILES": MILEAGE_TOLERANCE_MILES,
                "COLOR_MISMATCH_MAJORITY": COLOR_MISMATCH_MAJORITY,
            },
        },
        "rows": per_row_results,
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== Per-field-error detection (precision / recall / F1 by error_type) ===")
    for error_type, m in results["per_field_metrics"].items():
        print(f"  {error_type:20s} tp={m['tp']:<3d} fn={m['fn']:<3d} fp={m['fp']:<3d} "
              f"precision={m['precision']} recall={m['recall']} f1={m['f1']}")
    print(f"\nOverall verdict accuracy: {results['verdict_accuracy']}")
    print(f"\nFull results written to {RESULTS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["submit", "fetch-round1", "submit-round2", "fetch-round2"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.command == "submit":
        submit_round1(limit=args.limit)
    elif args.command == "fetch-round1":
        fetch_round1()
    elif args.command == "submit-round2":
        submit_round2()
    elif args.command == "fetch-round2":
        fetch_round2()
