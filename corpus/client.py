import re
import time
import urllib.parse

import requests

from corpus.config import HOST, API_VERSION, COMMENTS_KEY, PAGE_LIMIT, SLEEP_BETWEEN_PAGES
from corpus.auth import TiniToken
from corpus.signing import sign_request


def build_signed_url(path: str, params: dict, tini: TiniToken) -> str:
    timestamp = str(int(time.time() * 1000))
    params = dict(params)  # copy so we don't mutate the caller's dict
    params["timestamp"] = timestamp
    params["signature"] = sign_request(path, tini, timestamp)
    query = urllib.parse.urlencode(params)
    return f"{HOST}/{API_VERSION}/{path}?{query}"


def extract_auction_id(url_or_id: str) -> str:
    """Accepts either a full auction URL or a bare auction ID, returns the ID."""
    match = re.search(r"/auctions/([A-Za-z0-9]+)", url_or_id)
    if match:
        return match.group(1)
    return url_or_id.strip()


def fetch_comments_page(session: requests.Session, auction_id: str, tini: TiniToken, after_id: str = None) -> dict:
    path = f"autos/auctions/{auction_id}/comments"
    params = {"limit": PAGE_LIMIT, "filter": 1}
    if after_id:
        params["after_id"] = after_id
    url = build_signed_url(path, params, tini)
    resp = session.get(url)
    resp.raise_for_status()
    return resp.json()


def fetch_all_comments(session: requests.Session, auction_id: str, tini: TiniToken) -> list:
    all_comments = []
    after_id = None
    page_num = 0

    while True:
        page_num += 1
        page = fetch_comments_page(session, auction_id, tini, after_id=after_id)

        if COMMENTS_KEY not in page:
            raise KeyError(
                f"Expected key '{COMMENTS_KEY}' not found in the response. "
                f"Actual top-level keys: {list(page.keys())}. "
                f"Update COMMENTS_KEY near the top of this file to match, then re-run."
            )

        items = page[COMMENTS_KEY]
        print(f"    page {page_num}: got {len(items)} items")

        if not items:
            break

        all_comments.extend(items)

        last_item = items[-1]
        after_id = last_item.get("id")
        if after_id is None:
            print("    WARNING: last item has no 'id' field -- stopping pagination early. "
                  "Check the actual field name for a comment's ID in the Response tab.")
            break

        if len(items) < PAGE_LIMIT:
            # got fewer than we asked for -- reliable signal this was the last page
            break

        time.sleep(SLEEP_BETWEEN_PAGES)

    return all_comments
