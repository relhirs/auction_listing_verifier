import json
from dotenv import load_dotenv

load_dotenv()

from agents.extraction_agent import extract_listing
from agents.vin_agent import verify_vin
from agents.photo_agent import analyze_photos
from agents.editorial_agent import check_editorial
from core.verifier import verify_listing
from agents.synthesis_agent import synthesize_report
from corpus.sample_listings import EXAMPLE_LISTINGS

OUT_PATH = "eval/sample_reports_cache.json"


def build_cache_entry(listing_text: str, image_urls: list[str]) -> dict:
    listing_data, _, _ = extract_listing(listing_text)
    vin_data = verify_vin(listing_data.vin) if listing_data.vin else verify_vin("00000000000000000")
    editorial_data, _, _ = check_editorial(listing_text)

    photo_data = []
    duplicate_photo_pairs = []
    if image_urls:
        photo_data, _, _, duplicate_photo_pairs = analyze_photos(image_urls)

    flags, verification_summary = verify_listing(
        listing_data, vin_data, photo_data, editorial_data,
        duplicate_photo_pairs=duplicate_photo_pairs,
    )
    report, _, _ = synthesize_report(flags)

    return {
        "listing_data": listing_data.model_dump(mode="json"),
        "vin_data": vin_data.model_dump(mode="json"),
        "verification_summary": verification_summary.model_dump(mode="json"),
        "report": report.model_dump(mode="json"),
        "highlights_text": editorial_data.highlights_text,
        "completeness_score": editorial_data.completeness_score,
        "num_photos": len(image_urls),
        "num_duplicate_pairs": len(duplicate_photo_pairs),
    }


def main():
    # Resume from whatever is already cached, so a failure partway through
    # (a rate limit, a billing error, anything) never wastes the spend on
    # samples that already succeeded.
    try:
        with open(OUT_PATH) as f:
            cache = json.load(f)
        print(f"Resuming: {len(cache)} sample(s) already cached.")
    except FileNotFoundError:
        cache = {}

    for name, sample in EXAMPLE_LISTINGS.items():
        if name in cache:
            print(f"Skipping (already cached): {name}")
            continue
        print(f"Running pipeline for: {name}")
        cache[name] = build_cache_entry(sample["text"], sample["image_urls"])
        print(f"  -> {len(cache[name]['report']['flags'])} flag(s), "
              f"action={cache[name]['report']['recommended_action']}")
        # Write after every sample, not just at the end, so progress
        # survives a crash on a later sample.
        with open(OUT_PATH, "w") as f:
            json.dump(cache, f, indent=2)

    print(f"\nDone. {len(cache)} cached sample reports in {OUT_PATH}")


if __name__ == "__main__":
    main()
