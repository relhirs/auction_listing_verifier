import streamlit as st
import time
import json
import random
from dotenv import load_dotenv

# Still needed even though this app never calls the API: importing the
# agent modules below to reuse their Pydantic classes also constructs an
# Anthropic client at import time, which raises immediately if no API key
# is present in the environment.
load_dotenv()

from agents.extraction_agent import ListingData
from agents.vin_agent import VINData
from core.verifier import VerificationSummary
from agents.synthesis_agent import ListingReport
from corpus.sample_listings import EXAMPLE_LISTINGS, EXAMPLE_PLACEHOLDER

# --- Project links ---
DASHBOARD_URL = "https://listing-checker-ai.vercel.app/"
GITHUB_URL = "https://github.com/relhirs/auction_listing_verifier"
NHTSA_DECODER_URL = "https://vpic.nhtsa.dot.gov/decoder/"

# --- Cached sample reports, built once by generate_sample_cache.py. This
# app never calls the API itself: every result shown here was produced
# once, honestly, ahead of time, then replayed. There is no way to submit
# your own listing text or photo URLs, on purpose, so this can be shared
# publicly with no ongoing API cost no matter how many people use it.
try:
    with open("eval/sample_reports_cache.json") as f:
        SAMPLE_CACHE = json.load(f)
except FileNotFoundError:
    SAMPLE_CACHE = {}

# Short, plain-English explanations of how each check's confidence number
# is actually computed in core/verifier.py, so a viewer can see the
# reasoning behind a percentage instead of just the percentage itself.
CONFIDENCE_EXPLANATIONS = {
    "year": "This is a clean pass or fail check, so confidence is fixed at 0.95 whenever the VIN's decoded year does not match the claimed year.",
    "make": "A make mismatch is about as unambiguous as this system gets, so confidence is fixed at 0.99.",
    "engine_displacement": "Confidence scales with how far past the 0.2 liter tolerance the gap is, from a floor of 0.70 up to a ceiling of 0.95. A gap right at the edge of the tolerance reads as less certain than a large one.",
    "engine_cylinders": "Confidence scales with the size of the cylinder gap, from a floor of 0.70 up to a ceiling of 0.90. A 1 cylinder gap, often just a parsing quirk, counts as weaker evidence than a 2 or more cylinder gap.",
    "drivetrain": "Confidence is 0.90 for most mismatches, but floored to 0.70 specifically for AWD versus 4WD confusion, since that exact pair caused every false alarm this check has ever produced in testing. Every other kind of drivetrain mismatch has been correct 100% of the time.",
    "transmission": "Fixed at 0.80. NHTSA's transmission data is sparse enough that this check only fires when it actually has a real value to compare against.",
    "mileage": "Confidence scales with how far the service record's mileage exceeds the claimed mileage past a 5,000 mile tolerance, from a floor of 0.70 up to a ceiling of 0.95. A checkpoint just over the line reads as less certain than one tens of thousands of miles over it.",
    "color": "Fixed at 0.75 (or 0.30 near a close split) on purpose. Blending in the vision model's own confidence was tried and measured to make this check less accurate, not more, so it was left alone.",
    "duplicate_photo": "Confidence scales with how visually close the two photos are, based on hash distance, rather than one fixed number.",
    "photo_angles": "Confidence scales with how clearly the photo agent could identify the missing angle across all photos it analyzed, rather than one fixed number.",
}

# --- Page config ---
st.set_page_config(
    page_title="Cars & Bids Listing Verifier",
    page_icon="🚗",
    layout="wide"
)

# --- Initialize session state ---
if "report" not in st.session_state:
    st.session_state.report = None
if "running" not in st.session_state:
    st.session_state.running = False
if "highlights_text" not in st.session_state:
    st.session_state.highlights_text = None
if "verification_summary" not in st.session_state:
    st.session_state.verification_summary = None

# --- Sidebar ---
with st.sidebar:
    st.markdown("### About this project")
    st.caption(
        "This is the hands on demo half of a larger project. The same checks "
        "shown here were measured against 500 real, closed Cars & Bids auctions "
        "to see how well they actually catch planted mistakes."
    )
    st.markdown(f"[Full results and write up]({DASHBOARD_URL})")
    st.markdown(f"[Source on GitHub]({GITHUB_URL})")

# --- Header ---
st.title("Car Auction Listing Verifier")
st.write(
    "Pick one of the sample listings below to see the real output of the "
    "verification pipeline that scored 87.50% accuracy across 500 real "
    "closed auctions. Every result here is real, produced once ahead of "
    "time and replayed instantly, this page never calls the API live, so "
    "it works the same no matter how many people try it."
)

# --- Input section ---
st.subheader("Pick a sample")

sample_names = [EXAMPLE_PLACEHOLDER] + list(EXAMPLE_LISTINGS.keys())
selected_name = st.selectbox("Sample listing", options=sample_names, label_visibility="collapsed")

st.caption(
    "The first 10 samples are text only, testing the VIN and mileage checks. "
    "The last 5 use real photos from real closed auctions, testing the color, "
    "duplicate photo, and missing angle checks. "
    f"Every VIN below can be checked by hand at the [NHTSA VIN decoder]({NHTSA_DECODER_URL}) "
    "to confirm the result yourself."
)

selection_made = selected_name != EXAMPLE_PLACEHOLDER
run_clicked = st.button(
    "Run Analysis",
    type="primary",
    disabled=st.session_state.running or not selection_made,
)

if run_clicked and selection_made:
    st.session_state.running = True
    st.session_state.report = None

    sample = EXAMPLE_LISTINGS[selected_name]
    cached = SAMPLE_CACHE.get(selected_name)

    if cached is None:
        st.error(
            "This sample hasn't been cached yet. Run `python corpus/generate_sample_cache.py` "
            "(with API credits available) to generate it, then reload this page."
        )
        st.session_state.running = False
    else:
        image_urls = sample["image_urls"]

        STEPS = [
            "Extracting listing data...",
            "Verifying VIN...",
            "Analyzing photos...",
            "Checking editorial quality...",
            "Running verification logic...",
            "Generating report...",
        ]
        progress_bar = st.progress(0, text=STEPS[0])

        listing_data = ListingData.model_validate(cached["listing_data"])
        vin_data = VINData.model_validate(cached["vin_data"])
        verification_summary = VerificationSummary.model_validate(cached["verification_summary"])
        report = ListingReport.model_validate(cached["report"])

        time.sleep(random.uniform(0.8, 1.4))
        st.caption(f"Extracted: {listing_data.year} {listing_data.make} {listing_data.model}")
        progress_bar.progress(1 / len(STEPS), text=STEPS[1])

        time.sleep(random.uniform(0.5, 0.9))
        st.caption(f"VIN decoded: {vin_data.make} {vin_data.model} {vin_data.year}")
        progress_bar.progress(2 / len(STEPS), text=STEPS[2])

        if image_urls:
            time.sleep(random.uniform(0.4, 0.6) * len(image_urls))
            st.caption(f"Analyzed {len(image_urls)} photos")
            if cached.get("num_duplicate_pairs"):
                st.caption(f"{cached['num_duplicate_pairs']} possible duplicate photo pair(s) detected")
        else:
            time.sleep(random.uniform(0.2, 0.4))
            st.caption("No image URLs provided, skipping photo analysis.")
        progress_bar.progress(3 / len(STEPS), text=STEPS[3])

        time.sleep(random.uniform(0.7, 1.1))
        st.caption(f"Editorial score: {cached['completeness_score']}")
        progress_bar.progress(4 / len(STEPS), text=STEPS[4])

        time.sleep(random.uniform(0.2, 0.4))
        st.caption(f"Found {len(report.flags)} flag(s)")
        progress_bar.progress(5 / len(STEPS), text=STEPS[5])

        time.sleep(random.uniform(0.6, 1.0))
        progress_bar.progress(1.0, text="Done")

        st.session_state.report = report
        st.session_state.highlights_text = cached["highlights_text"]
        st.session_state.verification_summary = verification_summary
        st.session_state.running = False

# --- Results section ---
if st.session_state.report:
    report = st.session_state.report
    st.divider()
    st.subheader("Results")

    # --- Score and action ---
    col1, col2, col3 = st.columns(3)

    with col1:
        score = report.overall_score
        color = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🔴"
        st.metric("Overall Score", f"{color} {score:.0%}")

    with col2:
        action_colors = {
            "approve": "🟢 Approve",
            "needs_review": "🟡 Needs Review",
            "reject": "🔴 Reject"
        }
        st.metric("Recommended Action", action_colors[report.recommended_action])

    with col3:
        st.metric("Flags Found", len(report.flags))

    # --- What we verified ---
    if st.session_state.verification_summary:
        vs = st.session_state.verification_summary
        st.subheader("What we verified")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Year**")
            st.write(vs.year_claimed or "—")
            if vs.year_verified is True:
                st.markdown("✅ Confirmed by NHTSA")
            elif vs.year_verified is False:
                st.markdown(f"❌ Mismatch — NHTSA says {vs.year_verified_value}")
            else:
                st.markdown("— Not verified")
        with col2:
            st.markdown("**Make**")
            st.write(vs.make_claimed or "—")
            if vs.make_verified is True:
                st.markdown("✅ Confirmed by NHTSA")
            elif vs.make_verified is False:
                st.markdown(f"❌ Mismatch — NHTSA says {vs.make_verified_value}")
            else:
                st.markdown("— Not verified")
        with col3:
            st.markdown("**Engine**")
            st.write(vs.engine_claimed or "—")
            if vs.engine_verified is True:
                st.markdown("✅ Confirmed by NHTSA")
            elif vs.engine_verified is False:
                st.markdown(f"❌ Mismatch — NHTSA says {vs.engine_verified_value}")
            else:
                st.markdown("— Not verified")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Exterior color**")
            st.write(vs.color_claimed or "—")
            if vs.color_verified is True:
                st.markdown("✅ Matches photos")
            elif vs.color_verified is False:
                st.markdown(f"⚠️ Photos show {vs.color_observed}")
            else:
                st.markdown("— No exterior photos")
        with col2:
            st.markdown("**Mileage**")
            st.write(vs.mileage_claimed or "—")
            if vs.mileage_consistent is True:
                st.markdown("✅ Consistent with service history")
            elif vs.mileage_consistent is False:
                st.markdown(f"⚠️ Service record shows {vs.mileage_checkpoint} miles")
            else:
                st.markdown("— No service history in listing text")
        with col3:
            st.markdown("**VIN**")
            if vs.vin_decoded:
                st.markdown("✅ Decoded successfully")
            else:
                st.markdown("❌ Could not decode")
            st.caption(f"[Check this VIN yourself]({NHTSA_DECODER_URL})")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Photos**")
            st.write(f"{vs.photos_analyzed} photos analyzed")
            st.write(f"{vs.photos_with_damage} with visible damage noted")
            if vs.photos_with_damage > 0:
                for obs in vs.damage_observations[:5]:
                    st.caption(obs)
                if len(vs.damage_observations) > 5:
                    st.caption("...")
        with col2:
            st.markdown("**Editorial quality**")
            if vs.editorial_score is not None:
                st.write(f"{vs.editorial_score:.0%}")
                label_map = {"Strong": "✅ Strong", "Good": "✓ Good", "Needs work": "⚠️ Needs work"}
                st.write(label_map.get(vs.editorial_score_label, vs.editorial_score_label))

    # --- Summary ---
    st.subheader("Summary")
    st.write(report.summary_paragraph)

    # --- Generated Highlights ---
    if st.session_state.highlights_text:
        st.subheader("Generated highlights")
        st.text_area("highlights", value=st.session_state.highlights_text, height=200, label_visibility="collapsed")

    # --- Flag cards ---
    if report.flags:
        st.subheader("Flags")

        severity_icons = {"ERROR": "🔴", "WARNING": "🟡", "INFO": "🔵"}

        def render_flag_card(flag):
            icon = severity_icons[flag.severity]
            with st.expander(f"{icon} [{flag.severity}] {flag.field_name}", expanded=flag.severity == "ERROR"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Claimed Value**")
                    st.write(flag.claimed_value or "—")
                    st.markdown("**Source of Truth**")
                    st.write(flag.source_of_truth)
                with col2:
                    st.markdown("**Verified Value**")
                    st.write(flag.verified_value or "—")
                    st.markdown("**Confidence**")
                    st.write(f"{flag.confidence:.0%}")
                st.markdown("**Suggested Fix**")
                st.info(flag.suggested_fix)

                confidence_note = CONFIDENCE_EXPLANATIONS.get(flag.field_name)
                if confidence_note:
                    with st.expander("Why this confidence number?"):
                        st.caption(confidence_note)

        for flag in report.flags[:5]:
            render_flag_card(flag)

        if len(report.flags) > 5:
            with st.expander(f"Show {len(report.flags) - 5} more flags"):
                for flag in report.flags[5:]:
                    render_flag_card(flag)
    else:
        st.success("No flags detected. This listing looks clean.")
