"""
scrape_comments.py

Batch scraper for Cars & Bids auction comments.

HOW TO USE THIS:
1. Fill in AUCTION_URLS near the bottom with your batch of auction URLs or IDs.
2. Run: python -m corpus.scrape_comments
3. The script will:
   a. Run the self-test FIRST. If it fails, it stops -- it will not attempt
      the batch job with a formula it hasn't confirmed works.
   b. If the self-test passes, it fetches all comments for every auction in
      AUCTION_URLS, paginating automatically, and stores them in the
      raw_comments table of corpus/corpus.db (see corpus/storage.py).
4. Safe to re-run: any auction already stored gets skipped, so you can add
   more URLs to the list later and only the new ones get fetched. Saves are
   also idempotent per-comment (INSERT OR REPLACE keyed on auction_id +
   comment_id), so re-running an in-progress auction never creates duplicates.

IF YOU GET A KeyError ABOUT 'comments_and_bids' NOT BEING FOUND:
Open a row's comment_json in corpus/corpus.db, or re-check the Response tab in
DevTools, find the actual top-level key holding the array, and change
COMMENTS_KEY in corpus/config.py to match. This is the single most likely
thing to need adjusting -- I have not confirmed this key name against a live
response.

To re-run just the signature self-test on its own: python -m corpus.signing
"""

import time

import requests

from corpus.config import HEADERS, SLEEP_BETWEEN_AUCTIONS
from corpus.auth import get_ti_ni
from corpus.client import extract_auction_id, fetch_all_comments
from corpus.signing import self_test
from corpus.storage import init_db, has_auction, save_comments


def run_batch(urls_or_ids: list):
    if not urls_or_ids:
        print("AUCTION_URLS is empty -- nothing to do. Add some URLs near the bottom of this file.")
        return

    session = requests.Session()
    session.headers.update(HEADERS)

    tini = get_ti_ni(session)
    print(f"Got a fresh tini token: farsce starts with '{tini.farsce[:8]}...', "
          f"gi_ase starts with '{tini.gi_ase[:8]}...'\n")

    for i, raw in enumerate(urls_or_ids, 1):
        auction_id = extract_auction_id(raw)

        if has_auction(auction_id):
            print(f"[{i}/{len(urls_or_ids)}] {auction_id}: already cached, skipping")
            continue

        print(f"[{i}/{len(urls_or_ids)}] {auction_id}: fetching...")
        try:
            comments = fetch_all_comments(session, auction_id, tini)
            save_comments(auction_id, comments)
        except Exception as e:
            print(f"    ERROR on {auction_id}: {e}")
            print("    skipping this one, continuing with the rest of the batch")

        time.sleep(SLEEP_BETWEEN_AUCTIONS)

    print("\nBatch run finished.")


# Paste your batch of auction URLs or bare auction IDs here, one per line.
# Full URLs and bare IDs both work -- extract_auction_id() handles either.
AUCTION_URLS = [
    "https://carsandbids.com/auctions/3RJ7VvB8/1999-toyota-land-cruiser",
    "https://carsandbids.com/auctions/3qYgyXw4/1991-toyota-mr2-turbo",
    "https://carsandbids.com/auctions/rwOLM8Ew/1998-range-rover-40-se",
    "https://carsandbids.com/auctions/98BdjXoe/1995-subaru-sambar-fire-truck",
    "https://carsandbids.com/auctions/rJAlE6NK/2006-chrysler-300-limited-convertible-conversion",
    "https://carsandbids.com/auctions/3yZ15oDd/2002-bmw-m3-convertible",
    "https://carsandbids.com/auctions/9XD4j41j/1965-chevrolet-corvette-convertible",
    "https://carsandbids.com/auctions/rjg5kqNp/2016-chevrolet-camaro-2ss-coupe",
    "carsandbids.com/auctions/KdYkLEv1/",
    "carsandbids.com/auctions/9W5mpbRq/",
    "carsandbids.com/auctions/98BdjXoe/",
    "carsandbids.com/auctions/92QNPPNE/",
    "carsandbids.com/auctions/3yL17nkR/",
    "carsandbids.com/auctions/rwYoANmx/",
    "carsandbids.com/auctions/37N8y8N7/",
    "carsandbids.com/auctions/rbJGnjdd/",
    "carsandbids.com/auctions/9ANkLjGv/",
    "carsandbids.com/auctions/364yVlWP/",
    "carsandbids.com/auctions/3ozj6axw/",
    "carsandbids.com/auctions/9lXg7LNE/",
    "carsandbids.com/auctions/3pmXxRNe/",
    "carsandbids.com/auctions/rMXQjW8R/",
    "carsandbids.com/auctions/KPyOXev2/",
    "carsandbids.com/auctions/30RJvpRL/",
    "carsandbids.com/auctions/KmvGZbZm/",
    "carsandbids.com/auctions/9X7qwXal/",
    "carsandbids.com/auctions/KdQDjzzL/",
    "carsandbids.com/auctions/36OyNlBn/",
    "carsandbids.com/auctions/KDbw5NAE/",
    "carsandbids.com/auctions/3vpBZWmk/",
    "carsandbids.com/auctions/KVy86aXx/",
    "carsandbids.com/auctions/3z8VqdjA/",
    "carsandbids.com/auctions/KdBWbmB9/",
    "carsandbids.com/auctions/9elZ5W56/",
    "carsandbids.com/auctions/KVG8yWOY/",
    "carsandbids.com/auctions/3yQNXwgE/",
    "carsandbids.com/auctions/rbp1kgWw/",
    "carsandbids.com/auctions/3L4lgn03/",
    "carsandbids.com/auctions/9aLYqn1o/",
    "carsandbids.com/auctions/9QamNDzn/",
    "carsandbids.com/auctions/KYDkbqp5/",
    "carsandbids.com/auctions/KmqzQ4Jd/",
    "carsandbids.com/auctions/KmaEoQvb/",
    "carsandbids.com/auctions/92vXm4EJ/",
    "carsandbids.com/auctions/KPGom7Gk/",
    "carsandbids.com/auctions/rJJYb6Qz/",
    "carsandbids.com/auctions/KVMq1NbM/",
    "carsandbids.com/auctions/30EpRQbj/",
    "carsandbids.com/auctions/9XYy4yqq/",
    "carsandbids.com/auctions/KDzwA2zy/",
    "carsandbids.com/auctions/3v8B4AEj/",
    "carsandbids.com/auctions/KVqlkMW0/",
    "carsandbids.com/auctions/98gkaE40/",
    "carsandbids.com/auctions/3Bkn2gJb/",
    "carsandbids.com/auctions/rJOqjWp9/",
    "carsandbids.com/auctions/3BmOVdd4/",
    "carsandbids.com/auctions/9ldgWL5N/",
    "carsandbids.com/auctions/rby16Yby/",
    "carsandbids.com/auctions/9a0BpnQD/",
    "carsandbids.com/auctions/KDqw7Byo/",
    "carsandbids.com/auctions/rxOjZz50/",
    "carsandbids.com/auctions/rbeGYAJL/",
    "carsandbids.com/auctions/KZdnvp7R/"
]


if __name__ == "__main__":
    print("=== STEP 1: self-test the signature formula ===\n")
    if not self_test():
        print("\nSelf-test FAILED.")
        print("Do NOT run the batch job with these values -- the formula")
        print("isn't confirmed working yet. Re-check the pasted values for")
        print("stray quotes/whitespace, or bring the printed output back for help.")
    else:
        print("\nSelf-test PASSED.\n")
        print("=== STEP 2: batch fetching comments ===\n")
        init_db()
        run_batch(AUCTION_URLS)
