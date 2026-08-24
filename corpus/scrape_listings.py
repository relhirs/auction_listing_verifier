import json
import os
import re

TARGET_COUNT = 507
LISTINGS_PATH = os.path.join(os.path.dirname(__file__), "listings.json")
PAST_AUCTIONS_URL = "https://carsandbids.com/past-auctions/"
MULTI_WORD_MAKES = [
    "Alfa Romeo",
    "Aston Martin",
    "Land Rover",
    "Mercedes-Benz",
    "Rolls-Royce",
]

MODEL_LINE_TO_MAKE = {
    "Range Rover": "Land Rover",
}

STALL_LIMIT = 6  # consecutive pages with no new listings before giving up
SCROLL_WAIT_MS = 1500  # settle time after navigating to each page

BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def load_existing():
    """Returns (results_dict keyed by (year, make, model) -> url, ordered list of dicts)."""
    if not os.path.exists(LISTINGS_PATH):
        return {}, []
    with open(LISTINGS_PATH, "r") as f:
        data = json.load(f)
    results = {}
    ordered = []
    for entry in data:
        key = (entry["year"], entry["make"], entry["model"])
        results[key] = entry["url"]
        ordered.append(entry)
    return results, ordered


def atomic_write(ordered_entries):
    tmp_path = LISTINGS_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(ordered_entries, f, indent=2)
    os.replace(tmp_path, LISTINGS_PATH)


def parse_title(title: str):
    """Parse a listing title like '2019 Alfa Romeo Giulia Quadrifoglio' into
    (year, make, model). Returns None if it doesn't start with a 4-digit year."""
    title = title.strip()
    match = re.match(r"^(\d{4})\s+(.*)$", title)
    if not match:
        return None
    year, rest = match.group(1), match.group(2).strip()

    for prefix, mapped_make in MODEL_LINE_TO_MAKE.items():
        if rest.startswith(prefix + " ") or rest == prefix:
            return year, mapped_make, rest

    for multi_make in MULTI_WORD_MAKES:
        if rest.startswith(multi_make + " "):
            make = multi_make
            model = rest[len(multi_make):].strip()
            return year, make, model
        if rest == multi_make:
            return year, multi_make, ""

    parts = rest.split(" ", 1)
    if len(parts) == 1:
        return year, parts[0], ""
    make, model = parts[0], parts[1]
    return year, make, model


def main():
    results, ordered = load_existing()
    print(f"Loaded {len(results)} existing listings from {LISTINGS_PATH}")

    if len(results) >= TARGET_COUNT:
        print(f"Already have {len(results)} >= target {TARGET_COUNT}. Nothing to do.")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run:\n"
              "    pip install playwright && playwright install chromium")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)

        def block_heavy(route):
            if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_heavy)

        stall_count = 0
        page_num = 1

        while len(results) < TARGET_COUNT:
            page_url = f"{PAST_AUCTIONS_URL}?page={page_num}"
            print(f"Navigating to {page_url} ...")
            page.goto(page_url, wait_until="domcontentloaded")
            page.wait_for_timeout(SCROLL_WAIT_MS)

            anchors = page.eval_on_selector_all(
                'a[href^="/auctions/"]',
                "els => els.map(e => ({href: e.getAttribute('href'), text: e.innerText}))",
            )

            new_this_round = 0
            for a in anchors:
                href = a.get("href")
                text = a.get("text", "")
                if not href or not text:
                    continue

                parsed = parse_title(text)
                if parsed is None:
                    continue
                year, make, model = parsed
                key = (year, make, model)
                if key in results:
                    continue

                url = href if href.startswith("http") else f"https://carsandbids.com{href}"
                results[key] = url
                entry = {"year": year, "make": make, "model": model, "url": url}
                ordered.append(entry)
                new_this_round += 1

                if len(results) >= TARGET_COUNT:
                    break

            if new_this_round > 0:
                atomic_write(ordered)
                print(f"{len(results)}/{TARGET_COUNT} collected "
                      f"(+{new_this_round} this round, page {page_num})")
                stall_count = 0
            else:
                stall_count += 1
                print(f"No new listings on page {page_num} "
                      f"(stall {stall_count}/{STALL_LIMIT})")

            if len(results) >= TARGET_COUNT:
                break

            if not anchors:
                stall_count += 1

            if stall_count >= STALL_LIMIT:
                print(f"Stalled for {STALL_LIMIT} consecutive pages -- "
                      f"stopping with {len(results)}/{TARGET_COUNT} collected. "
                      "This likely means we've reached the end of available listings.")
                break

            page_num += 1

        browser.close()

    print(f"\nDone. {len(results)}/{TARGET_COUNT} listings saved to {LISTINGS_PATH}")


if __name__ == "__main__":
    main()
