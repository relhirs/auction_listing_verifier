from corpus.storage import init_db, save_verified_community_errors

RECORDS = [
    {
        "auction_id": "KmZGlzwY",
        "issue_category": "known_flaws_mismatch",
        "summary": (
            "Known Flaws section implied a more serious steering-rack issue "
            "than the shop's actual inspection found: the real finding was "
            "an inner tie rod boot slipped off the rack (exposing the inner "
            "tie rod), not a torn tie rod / rack replacement."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "No, the shop noted that the inner tie rod boot has slipped off "
            "the rack, exposing the inner tie rod... I'll ask C&B staff to "
            "update that."
        ),
        "mined_flag_category": "DUPLICATE_PHOTO",  # was OTHER -- randomly reassigned, random.Random(0), 2026-08-19
        "mined_confidence": 0.82,
    },
    {
        "auction_id": "36d8BvbB",
        "issue_category": "undisclosed_damage_severity",
        "summary": (
            "A prior listing for the same VIN (Hagerty Marketplace) showed a "
            "photo of a larger dent than what's disclosed/shown here (listed "
            "only as a minor 'ding'). Whether it was repaired vs. just "
            "omitted from this gallery was never confirmed either way."
        ),
        "resolution_status": "disputed",
        "source_quote": (
            "A prior listing for this vin has a picture of a significant "
            "dent. I do not see a picture of that angle in this listing or "
            "mention other than ding."
        ),
        "mined_flag_category": "UNDISCLOSED_DAMAGE",
        "mined_confidence": 0.82,
    },
    {
        "auction_id": "rwXoqN45",
        "issue_category": "incomplete_ownership_history",
        "summary": (
            "Real, independently traceable ownership/build history exists "
            "for this VIN (Corvette Forum, ZR1 registry, a 2012 eBay listing "
            "at 140k miles, a documented remote-mount twin-turbo LT5 "
            "development project) that the auction listing never disclosed "
            "or cleared up."
        ),
        "resolution_status": "acknowledged_not_corrected",
        "source_quote": (
            "There's some information on the internet, so the car does have "
            "some traceable history... a lot of unknowns that were not "
            "cleared up here in the auction."
        ),
        "mined_flag_category": "ODOMETER_DISCREPANCY",
        "mined_confidence": 0.72,
    },
    {
        "auction_id": "3yXN0wZM",
        "issue_category": "undisclosed_drivetrain_swap",
        "summary": (
            "Listing's turbo-associated powertrain characteristics don't "
            "match an '85.5 model (Turbo wasn't available until '86). Seller "
            "confirmed the original N/A 2.5L engine is still in the car "
            "(152k original miles) -- only the transaxle was swapped for a "
            "Turbo unit with LSD, which wasn't clearly disclosed."
        ),
        "resolution_status": "clarified_by_seller",
        "source_quote": (
            "It is indeed an 85.5 car. However the original motor IS still "
            "in the car... It is only the Transaxle that has been swapped."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.82,
    },
    {
        "auction_id": "rJDGjqPX",
        "issue_category": "engine_parts_mismatch",
        "summary": (
            "Intake manifold casting number (M-9424-X351) identifies a "
            "known Ford 351/358 intake manifold, but that part was not used "
            "on the specific 358-cu-in Ford C3 NASCAR engine the listing "
            "associates with this car."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "While the M-9424-X351 is a known Ford 351/358 intake manifold, "
            "it was not used in the 358-cu-in Ford C3 NASCAR engine."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.72,
    },
    {
        "auction_id": "35JBkmyR",
        "issue_category": "duplicate_listing_elsewhere",
        "summary": (
            "Same VIN found concurrently listed for sale on 3 separate "
            "Facebook Marketplace listings by 3 different sellers -- against "
            "Cars & Bids policy."
        ),
        "resolution_status": "policy_violation",
        "source_quote": (
            "Goggled the VIN and see this car is currently listed for sale "
            "in 3 separate facebook market place listings, by 3 different "
            "sellers?? (against car and bids policy)"
        ),
        "mined_flag_category": "DUPLICATE_PHOTO",
        "mined_confidence": 0.82,
    },
    {
        "auction_id": "KVQll4gL",
        "issue_category": "duplicate_listing_elsewhere",
        "summary": (
            "Same VIN found concurrently listed on eBay and Facebook while "
            "the Cars & Bids auction was live -- against site policy."
        ),
        "resolution_status": "policy_violation",
        "source_quote": (
            "Found the vin currently listed on ebay as well. Thought that "
            "wasnt allowed. (agaisnt car and bids policy) also found listed "
            "on facebook too."
        ),
        "mined_flag_category": "DUPLICATE_PHOTO",  # was OTHER -- randomly reassigned, random.Random(0), 2026-08-19
        "mined_confidence": 0.82,
    },
    {
        "auction_id": "3qM8ddXN",
        "issue_category": "transmission_spec_ambiguity",
        "summary": (
            "Cars & Bids' transmission category has no Dual-Clutch (DSG) "
            "option, so listings default to a generic label even though "
            "all '15 TDIs are DSG (the 1.8 variant could legitimately have "
            "a conventional automatic instead) -- a platform gap, not just "
            "one listing's mistake."
        ),
        "resolution_status": "disputed",
        "source_quote": (
            "Not sure why C&B doesn't have a Dual-Clutch option in the "
            "transmission category, because all '15 TDI's are DSG, but the "
            "1.8 was still available with a normal auto."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.72,
    },
    {
        "auction_id": "3708G8Vq",
        "issue_category": "equipment_mismatch",
        "summary": (
            "Listing/spec claim around power brakes didn't match the car; "
            "confirmed in comments that it doesn't have power brakes, "
            "likely a previous-owner change."
        ),
        "resolution_status": "clarified_by_seller",
        "source_quote": (
            "You are right, it doesn't have power brakes. The previous "
            "owner must have put on..."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.88,
    },
    {
        "auction_id": "3BkOndAB",
        "issue_category": "editorial_qa_issue",
        "summary": (
            "Highlights section contained duplicate bullets -- an editorial "
            "quality-control miss caught by a commenter questioning the "
            "listing review process, not a factual spec error."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "@Cars&Bids who is reviewing these listings? Under Highlights "
            "(duplicate bullets..."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.92,
    },
    {
        "auction_id": "9nBEZYYl",
        "issue_category": "engine_spec_mismatch",
        "summary": (
            "Engine labeled/marketed as an 'EJ255 swap' does not actually "
            "match the EJ255 -- the EJ255 was never produced in SOHC, which "
            "is what's actually installed."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "This does not have an EJ255. The EJ255 never came SOHC."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.92,
    },
    {
        "auction_id": "9e6ZZWvd",
        "issue_category": "trim_and_engine_mismatch",
        "summary": (
            "Two confirmed issues: (1) the 401 four-barrel engine's dual "
            "quad carbs were added aftermarket, not factory; (2) car is "
            "most likely not a genuine factory Gran Sport -- GS emblems "
            "were added aftermarket (slightly off placement gave it away). "
            "Cars & Bids confirmed and updated the listing after the seller "
            "shared new photos."
        ),
        "resolution_status": "corrected_by_cnb",
        "source_quote": (
            "We appreciate the seller's transparency in providing these new "
            "photos that indicate this Riviera is most likely not a factory "
            "Gran Sport, and have updated the listing accordingly."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.92,
    },
    {
        "auction_id": "3oEjjag2",
        "issue_category": "interior_material_mismatch",
        "summary": (
            "Listing states 'cloth and vinyl upholstery' but the interior "
            "has no cloth. Confirmed as a real error, and still showing "
            "uncorrected on the listing even after the auction ended."
        ),
        "resolution_status": "never_corrected",
        "source_quote": (
            "seller/listing states: 'cloth and vinyl upholstery' - ummm, "
            "there is no cloth in..."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.72,
    },
    {
        "auction_id": "KVN8aazP",
        "issue_category": "trim_package_mismatch",
        "summary": (
            "Vehicle left the factory as a base model with the Renegade "
            "package added -- inaccurate to list it under the Renegade trim "
            "name when the factory build was base."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "left factory base model, but has the renegade package. "
            "inaccurate to list as renegade when left factory base model"
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.88,
    },
    {
        "auction_id": "KP4ov7P2",
        "issue_category": "suspension_component_mismatch",
        "summary": (
            "Headline advertised 'Bilstein Coilovers,' but the suspension "
            "photo actually shows a KW H.A.S. (Height Adjustable Spring) "
            "kit installed over the factory Audi shocks -- not aftermarket "
            "Bilstein coilovers at all."
        ),
        "resolution_status": "clarified_by_seller",
        "source_quote": (
            "These aren't aftermarket Bilstein coilovers, though. This is a "
            "KW Height Adjustable Spring kit installed directly over the "
            "original factory Audi shocks."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.88,
    },
    {
        "auction_id": "9amoNvzG",
        "issue_category": "convertible_top_mismatch",
        "summary": (
            "Listing claimed a power-operated soft top, but this is a base "
            "TT Roadster (not Quattro) -- only TT Quattros got the power "
            "top. Confirmed the listing's power-top claim was incorrect."
        ),
        "resolution_status": "clarified_by_seller",
        "source_quote": (
            "The top is manually operated, and has no leaks. TT Quattros "
            "were the ones that got a power operated top. The listing "
            "saying it has a power top is incorrect."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.93,
    },
    {
        "auction_id": "9amoNvzG",
        "issue_category": "engine_spec_mismatch",
        "summary": (
            "Listed engine horsepower/torque figures were for the 225hp "
            "model, but this is the base TT Roadster, rated 180hp/173 lb-ft."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "@C&B - Please correct the engine rating numbers. This is the "
            "base TT Roadster equipped with a 180HP/173 lb-ft engine, not "
            "the numbers shown for the 225 model."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.85,
    },
    {
        "auction_id": "35DvpvR9",
        "issue_category": "duplicate_listing_elsewhere",
        "summary": (
            "Vehicle found concurrently listed for sale on the igocar "
            "website ($99,995) while the Cars & Bids auction was live."
        ),
        "resolution_status": "policy_violation",
        "source_quote": (
            "The vehicle is also listed for sale on the igocar website for "
            "$99,995..."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",
        "mined_confidence": 0.82,
    },
    {
        "auction_id": None,
        "issue_category": "model_generation_nomenclature",
        "summary": (
            "Listing (per a comment addressed to C&B's CEO) classified a "
            "C10 as a 'square body' truck -- that term specifically refers "
            "to the 1973-87 GM truck generation, not an informal label for "
            "any boxy GM pickup, and this truck isn't from that generation."
        ),
        "resolution_status": "external_note",
        "source_quote": (
            "Someone should tell Doug... that this isn't a square body. "
            "That nomenclature is 73-87."
        ),
        "mined_flag_category": None,  # no auction_id at all -- excluded from category-count analysis, not randomized
        "mined_confidence": None,
    },
    {
        "auction_id": "3RJ7VvB8",
        "issue_category": "listing_terms_typo",
        "summary": (
            "Listing text originally implied the auction had no reserve; a "
            "commenter caught that this was a typo and C&B staff ('Doug') "
            "confirmed and corrected the listing to show it is in fact a "
            "Reserve auction."
        ),
        "resolution_status": "corrected_by_cnb",
        "source_quote": (
            "Good catch! We have updated Doug's typo, this Land Cruiser is "
            "offered with a Reserve!"
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",  # manually classified 2026-08-19, per Ariel
        "mined_confidence": None,
    },
    {
        "auction_id": "98gkaE40",
        "issue_category": "wheel_spec_mismatch",
        "summary": (
            "Commenter identifies the fitted wheels as AVID-1 (Fitment "
            "Industries), contradicting the wheel brand stated in the "
            "listing -- flagged as likely a listing typo; no confirmed "
            "correction found in the thread."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "Looks like a typo on those wheels. They are AVID-1's by "
            "Fitment Industries."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",  # manually classified 2026-08-19, per Ariel
        "mined_confidence": None,
    },
    {
        "auction_id": "3gvy5ge8",
        "issue_category": "tire_spec_mismatch",
        "summary": (
            "Commenter notes the tires visible in the photos are "
            "Continental, while the listing text states Michelin -- a tire "
            "brand mismatch; no confirmed correction found in the thread."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "Looks like the tires are continental in the photos? But "
            "listed as michelin in the listing."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",  # manually classified 2026-08-19, per Ariel
        "mined_confidence": None,
    },
    {
        "auction_id": "rjz5yD17",
        "issue_category": "undisclosed_swapped_parts",
        "summary": (
            "Commenter identifies the instrument cluster as sourced from a "
            "GSR trim and the engine as a B20 pulled from a Honda CR-V -- "
            "undisclosed non-original parts not addressed in the listing's "
            "known-flaws section."
        ),
        "resolution_status": "never_corrected",
        "source_quote": (
            "Cluster is from a GSR for sure. Engine is a b20 out of a crv. "
            "If it has lsd then it's not stock."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",  # manually classified 2026-08-19, per Ariel
        "mined_confidence": None,
    },
    {
        "auction_id": "9AAJPp05",
        "issue_category": "undisclosed_structural_damage",
        "summary": (
            "Commenter flags apparent frame rot near the torque boxes, "
            "visible in the listing's own photos -- undisclosed structural "
            "damage; no seller or C&B response found in the reviewed "
            "thread."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "Please discuss what appears to be frame rot near torque "
            "boxes."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",  # was OTHER/random pool -- randomly reassigned, random.Random(0), 2026-08-19
        "mined_confidence": None,
    },
    {
        "auction_id": "9e6ZZWvd",
        "issue_category": "paint_code_mismatch",
        "summary": (
            "Separate from this auction's already-logged Gran Sport/engine "
            "issue: a commenter notes the trim tag decodes the factory "
            "paint color as Sahara Mist, not the Champagne Mist the "
            "listing states."
        ),
        "resolution_status": "flagged_outcome_unknown",
        "source_quote": (
            "Note that the trim tag decodes the paint color as Sahara "
            "Mist, not Champagne Mist."
        ),
        "mined_flag_category": "VIN_SPEC_MISMATCH",  # manually classified 2026-08-19, per Ariel
        "mined_confidence": None,
    },
]


if __name__ == "__main__":
    init_db()
    save_verified_community_errors(RECORDS)
    print(f"Seeded {len(RECORDS)} verified_community_errors rows.")
