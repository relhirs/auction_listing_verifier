import json
import os
import re
import sys
import time

PHOTO_SAMPLE_COUNTS = {
    "exterior": 4,
    "interior": 3,
    "mechanical": 4,
    "docs": 1,
    "other": 1,
}

SPEC_LABELS = {
    "Make": "make",
    "Model": "model",
    "Trim": "trim",
    "Engine": "engine",
    "Drivetrain": "drivetrain",
    "Mileage": "mileage",
    "Transmission": "transmission",
    "VIN": "vin",
    "Body Style": "body_style",
    "Title Status": "title_status",
    "Exterior Color": "exterior_color",
    "Interior Color": "interior_color",
    "Location": "location",
    "Seller": "seller",
    "Seller Type": "seller_type",
}

# Stray UI-button lines that can appear inside the spec block (e.g. a "Save"
# watchlist button rendered inline between two fields) -- skipped when
# looking for a label's value, not treated as data.
STRAY_LINES = {"Save", "Share", "Watch"}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def parse_year_from_title(title: str) -> int | None:
    match = re.match(r"^(\d{4})\b", title.strip())
    return int(match.group(1)) if match else None


def parse_spec_block(body_text: str) -> dict:
    """Parses the plain-text spec block (Make\\nPorsche\\nEngine\\n...) out of
    the full rendered page text into a flat dict keyed by SPEC_LABELS' values."""
    lines = [l.strip() for l in body_text.split("\n")]
    result = {v: None for v in SPEC_LABELS.values()}

    i = 0
    while i < len(lines):
        line = lines[i]
        if line in SPEC_LABELS:     
            field = SPEC_LABELS[line]
            j = i + 1
            while j < len(lines) and (lines[j] == "" or lines[j] in STRAY_LINES):
                j += 1
            if j < len(lines):
                result[field] = lines[j]
            i = j + 1
        else:
            i += 1

    # Mileage arrives as "19,500" -- strip to a plain int string here, real
    # int coercion happens downstream once this is loaded back out of storage.
    if result.get("mileage"):
        result["mileage"] = re.sub(r"[^\d]", "", result["mileage"]) or None

    return result

_HIGHLIGHTS_END_MARKERS = [
    "\nView the entire listing",
    "\nClosed Auction Stats",
    "\nComments & Bids",
    "\nSimilar Auctions",
]


def extract_highlights_text(body_text: str) -> str | None:
    """Everything after the "Highlights" label, up to (not including) the
    first trailing UI/section marker -- the free-text seller description
    block extraction_agent.py parses as prose. Without an upper bound this
    would run to the end of body_text and swallow comments, footer links,
    and related-listing text along with the real Highlights content (a real
    bug found while validating the eval pipeline against a scraped listing:
    seller_description came back as the entire rendered page)."""
    idx = body_text.find("\nHighlights\n")
    if idx == -1:
        return None
    start = idx + len("\nHighlights\n")

    end = len(body_text)
    for marker in _HIGHLIGHTS_END_MARKERS:
        marker_idx = body_text.find(marker, start)
        if marker_idx != -1:
            end = min(end, marker_idx)

    return body_text[start:end].strip()


def scrape_one_listing(page, url: str) -> dict:
    """Scrapes one auction detail page. `page` is a Playwright sync Page
    already configured with the right User-Agent."""
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    title = page.title()
    body_text = page.inner_text("body")

    specs = parse_spec_block(body_text)
    specs["year"] = parse_year_from_title(title)
    specs["seller_description"] = extract_highlights_text(body_text)

    photos = _collect_categorized_photos(page)

    return {
        "url": url,
        "page_title": title,
        **specs,
        "photos": photos,
    }


def _visible_lightbox_image_src(page) -> str | None:
    """PhotoSwipe keeps up to 3 <img> in the DOM (prev/current/next slide)
    but only renders the current one visibly -- offsetParent is null for
    the hidden ones. Returns the currently-displayed slide's src, or None."""
    return page.evaluate(
        """() => {
            const imgs = Array.from(document.querySelectorAll('.pswp img'));
            const visible = imgs.find(el => el.offsetParent !== null && el.src);
            return visible ? visible.src : null;
        }"""
    )


def _collect_categorized_photos(page) -> dict[str, list[dict]]:
    """Opens the "All Photos" gallery modal. Clicking a category tab does
    NOT filter a grid (that only happens transiently on first open) -- it
    switches into a single-photo PhotoSwipe lightbox scoped to that
    category, navigated with the right-arrow key. So for each of the 5 real
    categories: click its tab, then step forward with ArrowRight,
    capturing the currently-visible slide's src at each step, until
    PHOTO_SAMPLE_COUNTS[category] photos are collected (deduped by URL) or
    the category runs out of photos (arrow press stops changing the src).
    Returns {category: [{"url": ...}]}."""
    result = {cat: [] for cat in PHOTO_SAMPLE_COUNTS}

    all_photos_button = page.locator("text=All Photos").first
    if all_photos_button.count() == 0:
        return result
    all_photos_button.click()
    page.wait_for_timeout(2500)  
    seen = set()

    for category, count in PHOTO_SAMPLE_COUNTS.items():
        tab = page.locator(f"text=/^{category.capitalize()}( \\(\\d+\\))?$/").first
        if tab.count() == 0:
            continue
        try:
            tab.click(timeout=5000)
        except Exception:
            try:
                tab.click(timeout=5000, force=True)
            except Exception:
                continue
        page.wait_for_timeout(600)

        last_src = None
        stall_count = 0
        for _ in range(count * 5):
            src = _visible_lightbox_image_src(page)
            if src and src not in seen:
                seen.add(src)
                result[category].append({"url": src})
            if len(result[category]) >= count:
                break
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(700)
            new_src = _visible_lightbox_image_src(page)
            if new_src == last_src:
                stall_count += 1
                page.wait_for_timeout(500)
                new_src = _visible_lightbox_image_src(page)
                if new_src == last_src and stall_count >= 3:
                    break
            else:
                stall_count = 0
            last_src = new_src

    return result


LISTINGS_PATH = os.path.join(os.path.dirname(__file__), "listings.json")


def build_url_list() -> list:
    """Deduplicated union of corpus/listings.json and
    corpus/scrape_comments.py's FALLBACK_AUCTION_URLS, deduped by
    extract_auction_id() (not raw URL string) since a few auctions appear
    in both lists under the same ID. Order: listings.json entries first,
    then any FALLBACK_AUCTION_URLS auction not already covered."""
    from corpus.client import extract_auction_id
    from corpus.scrape_comments import FALLBACK_AUCTION_URLS

    urls = []
    if os.path.exists(LISTINGS_PATH):
        with open(LISTINGS_PATH, "r") as f:
            urls.extend(entry["url"] for entry in json.load(f))

    seen_ids = {extract_auction_id(u) for u in urls}
    for raw in FALLBACK_AUCTION_URLS:
        if extract_auction_id(raw) not in seen_ids:
            urls.append(raw)
            seen_ids.add(extract_auction_id(raw))

    return urls


def run_batch_scrape():
    from corpus.client import extract_auction_id
    from corpus.config import SLEEP_BETWEEN_AUCTIONS
    from corpus.storage import init_db, has_auction_detail, save_auction_detail

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run:\n"
              "    pip install playwright && playwright install chromium")
        sys.exit(1)

    init_db()
    urls = build_url_list()
    print(f"{len(urls)} distinct real auctions to consider.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)

        for i, raw in enumerate(urls, 1):
            auction_id = extract_auction_id(raw)

            if has_auction_detail(auction_id):
                print(f"[{i}/{len(urls)}] {auction_id}: already cached, skipping")
                continue

            url = raw if raw.startswith("http") else f"https://carsandbids.com/auctions/{auction_id}/"
            print(f"[{i}/{len(urls)}] {auction_id}: fetching...")
            try:
                detail = scrape_one_listing(page, url)
                save_auction_detail(auction_id, detail)
            except Exception as e:
                print(f"    ERROR on {auction_id}: {e}")
                print("    skipping this one, continuing with the rest of the batch")

            time.sleep(SLEEP_BETWEEN_AUCTIONS)

        browser.close()

    print("\nBatch run finished.")


def main():
    if len(sys.argv) == 2:
        url = sys.argv[1]

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("Playwright is not installed. Run:\n"
                  "    pip install playwright && playwright install chromium")
            sys.exit(1)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT)
            detail = scrape_one_listing(page, url)
            browser.close()

        print(json.dumps(detail, indent=2))
    elif len(sys.argv) == 1:
        run_batch_scrape()
    else:
        print("Usage:\n"
              "  python -m corpus.scrape_listing_details <auction_url>   # single-listing debug\n"
              "  python -m corpus.scrape_listing_details                # full batch, persists to corpus.db")
        sys.exit(1)


if __name__ == "__main__":
    main()
