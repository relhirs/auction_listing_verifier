import streamlit as st
import time
import pandas as pd
from agents.extraction_agent import extract_listing
from agents.vin_agent import verify_vin
from agents.photo_agent import analyze_photos
from agents.editorial_agent import check_editorial
from core.verifier import verify_listing
from agents.synthesis_agent import synthesize_report
from core.logger import RunLogger, get_summary_dict, save_flag_feedback, get_connection

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
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}
if "verification_summary" not in st.session_state:
    st.session_state.verification_summary = None


# --- Header ---
st.title("🚗 Cars & Bids Listing Verifier")
st.caption("Paste a listing and image URLs to run full verification.")

# --- Input section ---
st.subheader("Input")

listing_url = st.text_input(
    "Listing URL (optional — for logging only)",
    placeholder="https://carsandbids.com/auctions/..."
)

listing_text = st.text_area(
    "Paste listing text",
    height=300,
    placeholder="Paste the full Cars & Bids listing text here..."
)

image_urls_input = st.text_area(
    "Image URLs (one per line)",
    height=150,
    placeholder="https://media.carsandbids.com/..."
)

# --- Run button ---
run_clicked = st.button("Run Analysis", type="primary", disabled=st.session_state.running)

if run_clicked and listing_text.strip():
    st.session_state.running = True
    st.session_state.report = None

    image_urls = [
        url.strip()
        for url in image_urls_input.strip().splitlines()
        if url.strip()
    ]

    logger = RunLogger(listing_url=listing_url or None)

    with st.spinner("Running verification pipeline..."):
        # --- Extraction Agent ---
        with st.status("Extracting listing data...", expanded=False):
            logger.start_agent("extraction")
            listing_data, in_tok, out_tok = extract_listing(listing_text)
            logger.end_agent("extraction", input_tokens=in_tok, output_tokens=out_tok)
            st.write(f"✅ Extracted: {listing_data.year} {listing_data.make} {listing_data.model}")

        # --- VIN Agent ---
        with st.status("Verifying VIN...", expanded=False):
            logger.start_agent("vin")
            vin_data = verify_vin(listing_data.vin) if listing_data.vin else verify_vin("00000000000000000")
            logger.end_agent("vin", input_tokens=0, output_tokens=0)
            st.write(f"✅ VIN decoded: {vin_data.make} {vin_data.model} {vin_data.year}")

        # --- Photo Agent ---
        photo_data = []
        if image_urls:
            with st.status(f"Analyzing {len(image_urls)} photo(s)...", expanded=False):
                logger.start_agent("photo")
                photo_data, in_tok, out_tok = analyze_photos(image_urls)
                logger.end_agent("photo", input_tokens=in_tok, output_tokens=out_tok)
                st.write(f"✅ Analyzed {len(photo_data)} photos")
        else:
            st.info("No image URLs provided — skipping photo analysis.")

        # --- Editorial Agent ---
        with st.status("Checking editorial quality...", expanded=False):
            logger.start_agent("editorial")
            editorial_data, in_tok, out_tok = check_editorial(listing_text)
            logger.end_agent("editorial", input_tokens=in_tok, output_tokens=out_tok)
            st.write(f"✅ Editorial score: {editorial_data.completeness_score}")

        # --- Verifier ---
        with st.status("Running verification logic...", expanded=False):
            flags, verification_summary = verify_listing(listing_data, vin_data, photo_data, editorial_data)
            st.write(f"✅ Found {len(flags)} flag(s)")

        # --- Synthesis Agent ---
        with st.status("Generating report...", expanded=False):
            logger.start_agent("synthesis")
            report, in_tok, out_tok = synthesize_report(flags)
            logger.end_agent("synthesis", input_tokens=in_tok, output_tokens=out_tok)
            st.write("✅ Report ready")

    # Save to session state
    st.session_state.report = report
    st.session_state.highlights_text = editorial_data.highlights_text
    st.session_state.verification_summary = verification_summary
    st.session_state.running = False

    # Log the run
    error_count = sum(1 for f in flags if f.severity == "ERROR")
    warning_count = sum(1 for f in flags if f.severity == "WARNING")
    info_count = sum(1 for f in flags if f.severity == "INFO")
    logger.save(
        flag_count=len(flags),
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        recommended_action=report.recommended_action,
        overall_score=report.overall_score
    )
    conn = get_connection()
    run_id = conn.execute(
        "SELECT id FROM runs ORDER BY id DESC LIMIT 1"
    ).fetchone()["id"]
    conn.close()
    st.session_state.current_run_id = run_id

elif run_clicked and not listing_text.strip():
    st.warning("Please paste listing text before running.")

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
                st.markdown("✅ Odometer consistent")
            elif vs.mileage_consistent is False:
                st.markdown(f"⚠️ Odometer shows {vs.mileage_photo_read}")
            else:
                st.markdown("— No odometer photo")
        with col3:
            st.markdown("**VIN**")
            if vs.vin_decoded:
                st.markdown("✅ Decoded successfully")
            else:
                st.markdown("❌ Could not decode")

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

        def render_flag_card(flag, i):
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

                col1, col2, col3, _ = st.columns([1, 1, 1, 2])
                with col1:
                    if st.button("✅ Correct", key=f"correct_{i}"):
                        save_flag_feedback(st.session_state.get("current_run_id"), flag.field_name, flag.severity, "correct")
                        st.session_state.feedback_given[i] = "correct"
                        st.toast("Feedback saved")
                with col2:
                    if st.button("❌ False positive", key=f"fp_{i}"):
                        save_flag_feedback(st.session_state.get("current_run_id"), flag.field_name, flag.severity, "false_positive")
                        st.session_state.feedback_given[i] = "false_positive"
                        st.toast("Feedback saved")
                with col3:
                    if st.button("👁 Already known", key=f"known_{i}"):
                        save_flag_feedback(st.session_state.get("current_run_id"), flag.field_name, flag.severity, "already_known")
                        st.session_state.feedback_given[i] = "already_known"
                        st.toast("Feedback saved")

                note = st.text_input(
                    "Add note (optional)",
                    placeholder="Describe what the flag got wrong or right...",
                    key=f"note_{i}",
                    label_visibility="collapsed" if st.session_state.feedback_given.get(i) else "visible"
                )
                if st.button("Submit note", key=f"submit_{i}") and note:
                    existing = st.session_state.feedback_given.get(i)
                    if existing:
                        save_flag_feedback(st.session_state.get("current_run_id"), flag.field_name, flag.severity, existing, editor_note=note)
                    else:
                        save_flag_feedback(st.session_state.get("current_run_id"), flag.field_name, flag.severity, "custom", editor_note=note)
                    st.toast("Note saved")

                if st.session_state.feedback_given.get(i):
                    _labels = {"correct": "✅ Marked as correct",
                               "false_positive": "❌ Marked as false positive",
                               "already_known": "👁 Marked as already known"}
                    st.caption(_labels.get(st.session_state.feedback_given[i],
                                          f"Marked as {st.session_state.feedback_given[i]}"))

        for i, flag in enumerate(report.flags[:5]):
            render_flag_card(flag, i)

        if len(report.flags) > 5:
            with st.expander(f"Show {len(report.flags) - 5} more flags"):
                for i, flag in enumerate(report.flags[5:], start=5):
                    render_flag_card(flag, i)
    else:
        st.success("No flags detected. This listing looks clean.")

    # --- Observability summary ---
    st.divider()
    st.subheader("System Stats")
    with st.expander("View observability summary"):
        summary = get_summary_dict()
        n = summary["total_runs"]

        if n == 0:
            st.info("No runs logged yet.")
        else:
            # Column headers
            col_l, col_r = st.columns([1, 1])
            with col_l:
                st.markdown("**This listing**")
            with col_r:
                st.markdown("**All-time avg**")

            # Row 1: Cost
            col_l, col_r = st.columns([1, 1])
            with col_l:
                c = summary["latest_cost"]
                st.metric("Cost", f"${c:.4f}" if c is not None else "—")
            with col_r:
                st.metric("Cost", f"${summary['avg_cost']:.4f}")

            # Row 2: Runtime
            col_l, col_r = st.columns([1, 1])
            with col_l:
                s = summary["latest_total_s"]
                st.metric("Runtime", f"{s:.1f}s" if s is not None else "—")
            with col_r:
                st.metric("Runtime", f"{summary['avg_total_s']:.1f}s")

            # Row 3: Overall score
            col_l, col_r = st.columns([1, 1])
            with col_l:
                sc = summary["latest_overall_score"]
                st.metric("Overall Score", f"{sc:.2f}" if sc is not None else "—")
            with col_r:
                st.metric("Overall Score", f"{summary['avg_overall_score']:.2f}")

            # Row 4: Recommended action
            col_l, col_r = st.columns([1, 1])
            with col_l:
                st.metric("Recommended Action", summary["latest_recommended_action"] or "—")
            with col_r:
                ab = summary["action_breakdown"]
                most_common = max(ab, key=ab.get) if ab else "—"
                st.metric("Most Common Action", most_common)

            # Row 5: Flags found
            col_l, col_r = st.columns([1, 1])
            with col_l:
                fc = summary["latest_flag_count"]
                st.metric("Flags Found", fc if fc is not None else "—")
            with col_r:
                st.metric("Flags Found", f"{summary['avg_flags']:.1f} avg")

            # Row 6: Errors
            col_l, col_r = st.columns([1, 1])
            with col_l:
                ec = summary["latest_error_count"]
                st.metric("🔴 Errors", ec if ec is not None else "—")
            with col_r:
                st.metric("🔴 Errors", summary["total_errors"])

            # Row 7: Warnings
            col_l, col_r = st.columns([1, 1])
            with col_l:
                wc = summary["latest_warning_count"]
                st.metric("🟡 Warnings", wc if wc is not None else "—")
            with col_r:
                st.metric("🟡 Warnings", summary["total_warnings"])

            # Row 8: Info flags
            col_l, col_r = st.columns([1, 1])
            with col_l:
                ic = summary["latest_info_count"]
                st.metric("🔵 Info flags", ic if ic is not None else "—")
            with col_r:
                st.metric("🔵 Info flags", summary["total_infos"])

            # Agent timing table — this listing vs all-time avg, sorted by all-time avg desc
            latest_times = summary["latest_agent_times"] or {}
            st.dataframe(
                pd.DataFrame([
                    {
                        "Agent": a,
                        "This listing": f"{latest_times.get(a, 0):.1f}s",
                        "All-time avg": f"{v['seconds']:.1f}s",
                    }
                    for a, v in summary["agent_timings"]
                ]),
                hide_index=True, use_container_width=True
            )